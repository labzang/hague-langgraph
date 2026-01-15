"""
KoELECTRA 게이트웨이 라우터 - 게이트웨이 및 상태 관리 기능
이메일 입력 → KoELECTRA 판별 → 조건 분기 → 판독 에이전트 호출 or 즉시 응답
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import asyncio
import logging
from datetime import datetime
import uuid

# 로컬 imports
from app.service.spam_classifier.inference import SpamClassifier
from app.service.verdict_agent import (
    analyze_email_verdict,
    analyze_email_with_tools,
    quick_verdict,
    get_mcp_agent_wrapper,
    EmailInput,
    GatewayResponse,
    ProcessingSessionState
)

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mcp", tags=["Multi-Agent Communication Protocol"])

# 모델들은 verdict_agent 패키지로 이동됨

# 전역 서비스 인스턴스 및 상태 관리
spam_classifier = None
processing_sessions: Dict[str, ProcessingSessionState] = {}

def get_spam_classifier():
    """스팸 분류기 인스턴스 가져오기"""
    global spam_classifier
    if spam_classifier is None:
        try:
            spam_classifier = SpamClassifier(
                model_path="app/model/spam/lora/run_20260115_1313",
                base_model="monologg/koelectra-small-v3-discriminator"
            )
            logger.info("KoELECTRA 스팸 분류기 로드 완료")
        except Exception as e:
            logger.error(f"KoELECTRA 로드 실패: {e}")
            raise HTTPException(status_code=500, detail=f"KoELECTRA 초기화 실패: {e}")
    return spam_classifier

def create_session(email: EmailInput) -> str:
    """새로운 처리 세션 생성"""
    session_id = str(uuid.uuid4())
    session = ProcessingSessionState(
        session_id=session_id,
        email_input=email,
        start_time=datetime.now(),
        processing_steps=["session_created"]
    )
    processing_sessions[session_id] = session
    logger.info(f"새로운 세션 생성: {session_id}")
    return session_id

def get_session(session_id: str) -> Optional[ProcessingSessionState]:
    """세션 조회"""
    return processing_sessions.get(session_id)

def update_session(session_id: str, updates: Dict[str, Any]) -> bool:
    """세션 업데이트"""
    if session_id in processing_sessions:
        session = processing_sessions[session_id]
        for key, value in updates.items():
            if hasattr(session, key):
                setattr(session, key, value)
        return True
    return False

def cleanup_old_sessions(max_age_hours: int = 24):
    """오래된 세션 정리"""
    current_time = datetime.now()
    to_remove = []

    for session_id, session in processing_sessions.items():
        age = (current_time - session.start_time).total_seconds() / 3600
        if age > max_age_hours:
            to_remove.append(session_id)

    for session_id in to_remove:
        del processing_sessions[session_id]
        logger.info(f"오래된 세션 정리: {session_id}")

    return len(to_remove)

# 게이트웨이 핵심 로직
async def koelectra_gateway_analysis(email: EmailInput) -> Dict[str, Any]:
    """KoELECTRA 게이트웨이 분석"""
    try:
        logger.info("KoELECTRA 게이트웨이 분석 시작")

        classifier = get_spam_classifier()

        # 이메일 텍스트 결합
        email_text = f"{email.subject} {email.content}".strip()

        # KoELECTRA 추론
        result = await asyncio.to_thread(classifier.predict, email_text)

        logger.info(f"KoELECTRA 결과: 스팸={result['is_spam']}, 신뢰도={result['confidence']:.3f}")
        return result

    except Exception as e:
        logger.error(f"KoELECTRA 게이트웨이 오류: {e}")
        raise

def determine_routing(koelectra_result: Dict[str, Any]) -> str:
    """라우팅 결정 로직"""
    confidence = koelectra_result["confidence"]
    is_spam = koelectra_result["is_spam"]

    # 고신뢰도 정상 메일: 즉시 통과
    if not is_spam and confidence > 0.95:
        return "immediate_pass"

    # 고신뢰도 스팸: 즉시 차단
    elif is_spam and confidence > 0.95:
        return "immediate_block"

    # 중간 신뢰도: 판독 에이전트 호출
    else:
        return "verdict_agent"

# API 엔드포인트들
@router.post("/analyze-email", response_model=GatewayResponse)
async def analyze_email(email: EmailInput):
    """
    이메일 스팸 분석 메인 엔드포인트
    KoELECTRA 게이트웨이 → 조건 분기 → 판독 에이전트 호출
    """
    try:
        logger.info(f"이메일 분석 시작: {email.subject[:50]}...")

        # 세션 생성
        session_id = create_session(email)
        session = get_session(session_id)

        # 1. KoELECTRA 게이트웨이 분석
        koelectra_result = await koelectra_gateway_analysis(email)
        update_session(session_id, {
            "koelectra_result": koelectra_result,
            "confidence_score": koelectra_result["confidence"]
        })
        session.processing_steps.append("koelectra_completed")

        # 2. 라우팅 결정
        routing_decision = determine_routing(koelectra_result)
        session.processing_steps.append(f"routed_to_{routing_decision}")

        # 3. 조건부 판독 에이전트 호출 (툴 기반)
        verdict_result = None
        if routing_decision == "verdict_agent":
            logger.info("판독 에이전트 호출 (툴 기반)")
            try:
                # 툴 기반 분석 사용
                verdict_result = await analyze_email_with_tools(
                    email.subject,
                    email.content,
                    koelectra_result
                )
                update_session(session_id, {"verdict_result": verdict_result})
                session.processing_steps.append("tool_based_analysis_completed")
            except Exception as e:
                logger.warning(f"툴 기반 분석 실패, 기존 방식으로 대체: {e}")
                # 기존 워크플로우 방식으로 대체
                verdict_result = await analyze_email_verdict(
                    email.subject,
                    email.content,
                    koelectra_result
                )
                update_session(session_id, {"verdict_result": verdict_result})
                session.processing_steps.extend(verdict_result.get("processing_steps", []))

        # 4. 최종 결정
        final_is_spam, final_confidence = _make_final_decision(
            koelectra_result, verdict_result, routing_decision
        )

        # 5. 세션 완료
        update_session(session_id, {
            "status": "completed",
            "end_time": datetime.now(),
            "final_decision": routing_decision
        })

        # 응답 구성
        response = GatewayResponse(
            is_spam=final_is_spam,
            confidence=final_confidence,
            koelectra_decision=f"{'스팸' if koelectra_result['is_spam'] else '정상'} (신뢰도: {koelectra_result['confidence']:.3f})",
            exaone_analysis=verdict_result.get("exaone_response") if verdict_result else None,
            processing_path=" → ".join(session.processing_steps),
            timestamp=datetime.now(),
            metadata={
                "session_id": session_id,
                "koelectra_result": koelectra_result,
                "verdict_result": verdict_result,
                "routing_decision": routing_decision
            }
        )

        logger.info(f"분석 완료: 스팸={final_is_spam}, 라우팅={routing_decision}")
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"이메일 분석 중 오류: {e}")
        # 세션 오류 상태 업데이트
        if 'session_id' in locals():
            update_session(session_id, {
                "status": "error",
                "error": str(e),
                "end_time": datetime.now()
            })
        raise HTTPException(status_code=500, detail=f"분석 처리 오류: {str(e)}")

def _make_final_decision(
    koelectra_result: Dict[str, Any],
    verdict_result: Optional[Dict[str, Any]],
    routing_decision: str
) -> tuple[bool, float]:
    """최종 결정 로직"""
    base_confidence = koelectra_result["confidence"]

    if routing_decision == "immediate_pass":
        return False, base_confidence
    elif routing_decision == "immediate_block":
        return True, base_confidence
    elif routing_decision == "verdict_agent" and verdict_result:
        # 판독 에이전트 결과 적용
        verdict = verdict_result.get("verdict", "uncertain")
        confidence_adjustment = verdict_result.get("confidence_adjustment", 0.0)

        if verdict == "spam":
            return True, min(0.99, base_confidence + confidence_adjustment)
        elif verdict == "normal":
            return False, min(0.99, base_confidence + confidence_adjustment)
        else:
            # 불확실한 경우 KoELECTRA 결과 사용
            return koelectra_result["is_spam"], base_confidence
    else:
        # 기본값: KoELECTRA 결과 사용
        return koelectra_result["is_spam"], base_confidence

@router.get("/sessions/{session_id}")
async def get_session_status(session_id: str):
    """세션 상태 조회"""
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다")

    processing_time = None
    if session.start_time and session.end_time:
        processing_time = (session.end_time - session.start_time).total_seconds()

    return {
        "session_id": session_id,
        "status": session.status,
        "processing_steps": session.processing_steps,
        "start_time": session.start_time,
        "end_time": session.end_time,
        "processing_time": processing_time,
        "koelectra_result": session.koelectra_result,
        "verdict_result": session.verdict_result,
        "error": session.error
    }

@router.get("/sessions")
async def list_sessions(limit: int = 50):
    """세션 목록 조회"""
    # 최근 세션들만 반환
    sorted_sessions = sorted(
        processing_sessions.items(),
        key=lambda x: x[1].start_time,
        reverse=True
    )[:limit]

    return {
        "total_sessions": len(processing_sessions),
        "returned_sessions": len(sorted_sessions),
        "sessions": [
            {
                "session_id": session_id,
                "status": session.status,
                "start_time": session.start_time,
                "email_subject": session.email_input.subject[:50] + "..." if len(session.email_input.subject) > 50 else session.email_input.subject,
                "final_decision": session.final_decision
            }
            for session_id, session in sorted_sessions
        ]
    }

@router.delete("/sessions/cleanup")
async def cleanup_sessions(max_age_hours: int = 24):
    """오래된 세션 정리"""
    cleaned_count = cleanup_old_sessions(max_age_hours)
    return {
        "message": f"{cleaned_count}개의 오래된 세션이 정리되었습니다",
        "remaining_sessions": len(processing_sessions),
        "max_age_hours": max_age_hours
    }

@router.get("/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    try:
        # 서비스 상태 확인
        koelectra_status = "OK" if spam_classifier else "Not Loaded"

        # 세션 통계
        session_stats = {
            "total": len(processing_sessions),
            "processing": len([s for s in processing_sessions.values() if s.status == "processing"]),
            "completed": len([s for s in processing_sessions.values() if s.status == "completed"]),
            "error": len([s for s in processing_sessions.values() if s.status == "error"])
        }

        return {
            "status": "healthy",
            "services": {
                "koelectra": koelectra_status,
                "verdict_agent": "Available"
            },
            "sessions": session_stats,
            "timestamp": datetime.now()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"헬스 체크 실패: {str(e)}")

@router.get("/gateway-info")
async def get_gateway_info():
    """게이트웨이 정보 조회"""
    return {
        "gateway_type": "KoELECTRA Spam Detection Gateway",
        "components": {
            "gateway": {
                "name": "KoELECTRA Gateway",
                "model": "monologg/koelectra-small-v3-discriminator",
                "adapter": "LoRA Fine-tuned",
                "role": "Primary spam classification"
            },
            "verdict_agent": {
                "name": "EXAONE Verdict Agent",
                "model": "EXAONE-2.4B",
                "role": "Detailed analysis for uncertain cases"
            }
        },
        "processing_flow": [
            "Email Input",
            "KoELECTRA Gateway Analysis",
            "Routing Decision",
            "Conditional Verdict Agent Call",
            "Final Decision"
        ],
        "routing_thresholds": {
            "immediate_pass": "> 95% confidence (normal)",
            "immediate_block": "> 95% confidence (spam)",
            "verdict_agent": "≤ 95% confidence (uncertain)"
        },
        "session_management": {
            "tracking": "UUID-based session tracking",
            "cleanup": "Automatic cleanup of old sessions",
            "monitoring": "Real-time session status monitoring"
        }
    }

@router.get("/stats")
async def get_gateway_stats():
    """게이트웨이 통계 조회"""
    try:
        # 세션 통계 계산
        total_sessions = len(processing_sessions)

        if total_sessions == 0:
            return {
                "total_sessions": 0,
                "message": "아직 처리된 세션이 없습니다"
            }

        # 상태별 통계
        status_counts = {}
        routing_counts = {}

        for session in processing_sessions.values():
            # 상태별 카운트
            status = session.status
            status_counts[status] = status_counts.get(status, 0) + 1

            # 라우팅별 카운트
            if session.final_decision:
                routing_counts[session.final_decision] = routing_counts.get(session.final_decision, 0) + 1

        # 평균 처리 시간 계산
        completed_sessions = [s for s in processing_sessions.values() if s.status == "completed" and s.end_time]
        avg_processing_time = None
        if completed_sessions:
            total_time = sum((s.end_time - s.start_time).total_seconds() for s in completed_sessions)
            avg_processing_time = total_time / len(completed_sessions)

        return {
            "total_sessions": total_sessions,
            "status_distribution": status_counts,
            "routing_distribution": routing_counts,
            "average_processing_time": f"{avg_processing_time:.2f}초" if avg_processing_time else "N/A",
            "completed_sessions": len(completed_sessions)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"통계 조회 실패: {str(e)}")

@router.get("/tools")
async def get_available_tools():
    """사용 가능한 EXAONE 툴 목록 조회"""
    try:
        mcp_wrapper = get_mcp_agent_wrapper()
        tools = mcp_wrapper.get_available_tools()

        tool_info = []
        for tool_name in tools:
            info = mcp_wrapper.get_tool_info(tool_name)
            tool_info.append(info)

        return {
            "available_tools": tools,
            "tool_details": tool_info,
            "total_tools": len(tools)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"툴 정보 조회 실패: {str(e)}")

@router.post("/tools/{tool_name}/execute")
async def execute_tool(tool_name: str, payload: Dict[str, Any]):
    """특정 툴 직접 실행"""
    try:
        mcp_wrapper = get_mcp_agent_wrapper()

        # 툴 실행
        result = await mcp_wrapper.execute_tool(tool_name, **payload)

        return {
            "tool_name": tool_name,
            "payload": payload,
            "result": result,
            "timestamp": datetime.now()
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"툴 실행 실패: {str(e)}")
