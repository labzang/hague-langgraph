"""
EXAONE 기반 판독 에이전트 - LangGraph 워크플로우
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from pydantic import BaseModel

# LangGraph 관련 imports
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.tools import tool
from langchain_core.runnables import RunnableLambda

# 로컬 imports
from app.service.exaone.chat_service import ExaoneService
from .state_model import VerdictState

logger = logging.getLogger(__name__)

# VerdictState는 state_model.py에서 import됨

# 전역 EXAONE 서비스 인스턴스
_exaone_service = None

def get_exaone_service() -> ExaoneService:
    """EXAONE 서비스 인스턴스 가져오기"""
    global _exaone_service
    if _exaone_service is None:
        try:
            _exaone_service = ExaoneService()
            logger.info("EXAONE 판독 서비스 초기화 완료")
        except Exception as e:
            logger.error(f"EXAONE 서비스 초기화 실패: {e}")
            raise
    return _exaone_service

# EXAONE 툴 래핑
@tool
async def exaone_spam_analyzer(prompt: str) -> str:
    """
    EXAONE 기반 스팸 분석 툴

    Args:
        prompt: 분석할 이메일 정보가 포함된 프롬프트

    Returns:
        EXAONE의 분석 결과
    """
    try:
        logger.info("EXAONE 스팸 분석 툴 실행")
        exaone_service = get_exaone_service()
        result = await exaone_service.generate_response(prompt)
        logger.info("EXAONE 스팸 분석 툴 완료")
        return result
    except Exception as e:
        logger.error(f"EXAONE 스팸 분석 툴 오류: {e}")
        return f"분석 중 오류 발생: {str(e)}"

@tool
async def exaone_quick_verdict(email_text: str, koelectra_confidence: float) -> str:
    """
    EXAONE 빠른 판정 툴

    Args:
        email_text: 이메일 텍스트
        koelectra_confidence: KoELECTRA 신뢰도

    Returns:
        빠른 판정 결과
    """
    try:
        logger.info("EXAONE 빠른 판정 툴 실행")

        prompt = f"""
다음 이메일에 대한 빠른 스팸 판정을 해주세요.

이메일 내용: {email_text}
1차 AI 신뢰도: {koelectra_confidence:.3f}

간단히 다음 중 하나로 답변해주세요:
- 정상: 안전한 이메일
- 스팸: 스팸 메일
- 불확실: 추가 분석 필요

판정 근거를 2-3줄로 간단히 설명해주세요.
"""

        exaone_service = get_exaone_service()
        result = await exaone_service.generate_response(prompt)
        logger.info("EXAONE 빠른 판정 툴 완료")
        return result
    except Exception as e:
        logger.error(f"EXAONE 빠른 판정 툴 오류: {e}")
        return f"판정 중 오류 발생: {str(e)}"

@tool
async def exaone_detailed_analyzer(
    email_subject: str,
    email_content: str,
    koelectra_result: Dict[str, Any]
) -> str:
    """
    EXAONE 상세 분석 툴

    Args:
        email_subject: 이메일 제목
        email_content: 이메일 내용
        koelectra_result: KoELECTRA 분석 결과

    Returns:
        상세 분석 결과
    """
    try:
        logger.info("EXAONE 상세 분석 툴 실행")

        # 이메일 정보 구성
        email_text = f"제목: {email_subject}\n내용: {email_content}"
        koelectra_info = f"KoELECTRA 판별: {'스팸' if koelectra_result.get('is_spam') else '정상'} (신뢰도: {koelectra_result.get('confidence', 0):.3f})"

        prompt = f"""
당신은 이메일 보안 전문가입니다. 다음 이메일에 대한 정밀 스팸 분석을 수행해주세요.

=== 이메일 정보 ===
{email_text}

=== 1차 AI 분석 결과 ===
{koelectra_info}
정상 확률: {koelectra_result.get('probabilities', {}).get('정상', 0):.3f}
스팸 확률: {koelectra_result.get('probabilities', {}).get('스팸', 0):.3f}

=== 분석 요청사항 ===
다음 관점에서 종합적으로 분석해주세요:

1. **발신자 신뢰성 분석**
   - 이메일 주소의 합법성
   - 도메인의 신뢰성
   - 발신자 정보의 일관성

2. **내용 진정성 분석**
   - 문체와 어조의 자연스러움
   - 맞춤법과 문법의 정확성
   - 내용의 논리적 일관성

3. **피싱/사기 위험성**
   - 개인정보 요구 여부
   - 금전 관련 요구사항
   - 긴급성을 강조하는 표현
   - 의심스러운 링크나 첨부파일

4. **광고성 여부**
   - 상업적 목적의 내용
   - 과도한 홍보 문구
   - 할인/이벤트 관련 내용

=== 결론 ===
최종 판단과 그 근거를 명확히 제시하고, 다음 중 하나로 분류해주세요:
- **정상**: 안전한 이메일로 판단
- **스팸**: 스팸으로 분류 권장
- **보류**: 추가 검토 필요

분석 결과를 구체적이고 명확하게 설명해주세요.
"""

        exaone_service = get_exaone_service()
        result = await exaone_service.generate_response(prompt)
        logger.info("EXAONE 상세 분석 툴 완료")
        return result
    except Exception as e:
        logger.error(f"EXAONE 상세 분석 툴 오류: {e}")
        return f"분석 중 오류 발생: {str(e)}"

# 툴 설정
exaone_tools = [
    exaone_spam_analyzer,
    exaone_quick_verdict,
    exaone_detailed_analyzer
]

# 간단한 툴 실행기 구현
class SimpleToolExecutor:
    """간단한 툴 실행기"""

    def __init__(self, tools):
        self.tools = {tool.name: tool for tool in tools}

    async def execute(self, tool_name: str, **kwargs):
        """툴 실행"""
        if tool_name not in self.tools:
            raise ValueError(f"툴 '{tool_name}'을 찾을 수 없습니다")

        tool = self.tools[tool_name]
        return await tool.ainvoke(kwargs)

tool_executor = SimpleToolExecutor(exaone_tools)

# MCP 라우터 에이전트 래핑
class MCPAgentWrapper:
    """MCP 라우터 에이전트를 툴로 래핑하는 클래스"""

    def __init__(self):
        self.tools = exaone_tools
        self.tool_executor = tool_executor
        logger.info("MCP 에이전트 래퍼 초기화 완료")

    async def execute_tool(self, tool_name: str, **kwargs) -> str:
        """특정 툴 실행"""
        try:
            # 툴 이름으로 툴 찾기
            tool_map = {tool.name: tool for tool in self.tools}

            if tool_name not in tool_map:
                available_tools = list(tool_map.keys())
                raise ValueError(f"툴 '{tool_name}'을 찾을 수 없습니다. 사용 가능한 툴: {available_tools}")

            selected_tool = tool_map[tool_name]
            result = await selected_tool.ainvoke(kwargs)

            logger.info(f"툴 '{tool_name}' 실행 완료")
            return result

        except Exception as e:
            logger.error(f"툴 '{tool_name}' 실행 오류: {e}")
            raise

    async def analyze_with_exaone(
        self,
        email_subject: str,
        email_content: str,
        koelectra_result: Dict[str, Any],
        analysis_type: str = "detailed"
    ) -> Dict[str, Any]:
        """EXAONE을 사용한 이메일 분석 (MCP 라우터용)"""
        try:
            logger.info(f"MCP 에이전트 래퍼: {analysis_type} 분석 시작")

            if analysis_type == "detailed":
                response = await self.execute_tool(
                    "exaone_detailed_analyzer",
                    email_subject=email_subject,
                    email_content=email_content,
                    koelectra_result=koelectra_result
                )
            else:
                email_text = f"{email_subject} {email_content}"
                confidence = koelectra_result.get("confidence", 0.0)
                response = await self.execute_tool(
                    "exaone_quick_verdict",
                    email_text=email_text,
                    koelectra_confidence=confidence
                )

            # 응답 분석
            response_lower = response.lower()
            if "스팸" in response_lower or "차단" in response_lower:
                verdict = "spam"
                confidence_adjustment = 0.1
            elif "정상" in response_lower or "안전" in response_lower:
                verdict = "normal"
                confidence_adjustment = 0.1
            elif "불확실" in response_lower or "보류" in response_lower:
                verdict = "uncertain"
                confidence_adjustment = 0.0
            else:
                # KoELECTRA 결과 따름
                verdict = "spam" if koelectra_result.get("is_spam") else "normal"
                confidence_adjustment = 0.05

            result = {
                "verdict": verdict,
                "confidence_adjustment": confidence_adjustment,
                "analysis_type": analysis_type,
                "exaone_response": response,
                "analysis_summary": f"EXAONE 툴 분석: {verdict} (신뢰도 조정: +{confidence_adjustment:.2f})",
                "tool_used": "exaone_detailed_analyzer" if analysis_type == "detailed" else "exaone_quick_verdict"
            }

            logger.info(f"MCP 에이전트 래퍼 분석 완료: {verdict}")
            return result

        except Exception as e:
            logger.error(f"MCP 에이전트 래퍼 분석 오류: {e}")
            raise

    def get_available_tools(self) -> List[str]:
        """사용 가능한 툴 목록 반환"""
        return [tool.name for tool in self.tools]

    def get_tool_info(self, tool_name: str) -> Dict[str, Any]:
        """특정 툴의 정보 반환"""
        tool_map = {tool.name: tool for tool in self.tools}

        if tool_name not in tool_map:
            return {"error": f"툴 '{tool_name}'을 찾을 수 없습니다"}

        tool = tool_map[tool_name]
        return {
            "name": tool.name,
            "description": tool.description,
            "args_schema": tool.args_schema.schema() if tool.args_schema else None
        }

# 전역 MCP 에이전트 래퍼 인스턴스
_mcp_agent_wrapper = None

def get_mcp_agent_wrapper() -> MCPAgentWrapper:
    """MCP 에이전트 래퍼 인스턴스 가져오기"""
    global _mcp_agent_wrapper
    if _mcp_agent_wrapper is None:
        _mcp_agent_wrapper = MCPAgentWrapper()
        logger.info("새로운 MCP 에이전트 래퍼 인스턴스 생성")
    return _mcp_agent_wrapper

# LangGraph 노드 함수들
async def initialize_analysis_node(state: VerdictState) -> VerdictState:
    """분석 초기화 노드"""
    try:
        logger.info("EXAONE 판독 분석 초기화")
        state.start_time = datetime.now()
        state.processing_steps.append("analysis_initialized")

        # KoELECTRA 결과 기반 분석 타입 결정
        confidence = state.koelectra_result.get("confidence", 0.0)

        if confidence > 0.8:
            state.analysis_type = "quick"
            state.processing_steps.append("quick_analysis_selected")
        else:
            state.analysis_type = "detailed"
            state.processing_steps.append("detailed_analysis_selected")

        logger.info(f"분석 타입 결정: {state.analysis_type}")
        return state

    except Exception as e:
        logger.error(f"분석 초기화 오류: {e}")
        state.error = f"초기화 오류: {str(e)}"
        return state

async def generate_prompt_node(state: VerdictState) -> VerdictState:
    """프롬프트 생성 노드"""
    try:
        logger.info("EXAONE 프롬프트 생성 시작")
        state.processing_steps.append("prompt_generation_started")

        # 이메일 정보 구성
        email_text = f"제목: {state.email_subject}\n내용: {state.email_content}"
        koelectra_info = f"KoELECTRA 판별: {'스팸' if state.koelectra_result.get('is_spam') else '정상'} (신뢰도: {state.koelectra_result.get('confidence', 0):.3f})"

        if state.analysis_type == "detailed":
            # 상세 분석 프롬프트
            state.exaone_prompt = f"""
당신은 이메일 보안 전문가입니다. 다음 이메일에 대한 정밀 스팸 분석을 수행해주세요.

=== 이메일 정보 ===
{email_text}

=== 1차 AI 분석 결과 ===
{koelectra_info}
정상 확률: {state.koelectra_result.get('probabilities', {}).get('정상', 0):.3f}
스팸 확률: {state.koelectra_result.get('probabilities', {}).get('스팸', 0):.3f}

=== 분석 요청사항 ===
다음 관점에서 종합적으로 분석해주세요:

1. **발신자 신뢰성 분석**
   - 이메일 주소의 합법성
   - 도메인의 신뢰성
   - 발신자 정보의 일관성

2. **내용 진정성 분석**
   - 문체와 어조의 자연스러움
   - 맞춤법과 문법의 정확성
   - 내용의 논리적 일관성

3. **피싱/사기 위험성**
   - 개인정보 요구 여부
   - 금전 관련 요구사항
   - 긴급성을 강조하는 표현
   - 의심스러운 링크나 첨부파일

4. **광고성 여부**
   - 상업적 목적의 내용
   - 과도한 홍보 문구
   - 할인/이벤트 관련 내용

=== 결론 ===
최종 판단과 그 근거를 명확히 제시하고, 다음 중 하나로 분류해주세요:
- **정상**: 안전한 이메일로 판단
- **스팸**: 스팸으로 분류 권장
- **보류**: 추가 검토 필요

분석 결과를 구체적이고 명확하게 설명해주세요.
"""
        else:
            # 빠른 분석 프롬프트
            state.exaone_prompt = f"""
다음 이메일에 대한 빠른 스팸 판정을 해주세요.

이메일 내용: {email_text}
1차 AI 결과: {koelectra_info}

간단히 다음 중 하나로 답변하고 2-3줄로 근거를 설명해주세요:
- 정상: 안전한 이메일
- 스팸: 스팸 메일
- 불확실: 추가 분석 필요
"""

        state.processing_steps.append("prompt_generated")
        logger.info(f"프롬프트 생성 완료: {state.analysis_type} 타입")
        return state

    except Exception as e:
        logger.error(f"프롬프트 생성 오류: {e}")
        state.error = f"프롬프트 생성 오류: {str(e)}"
        return state

async def exaone_analysis_node(state: VerdictState) -> VerdictState:
    """EXAONE 분석 실행 노드 (툴 사용)"""
    try:
        logger.info("EXAONE 분석 실행 시작 (툴 사용)")
        state.processing_steps.append("exaone_tool_analysis_started")

        # 분석 타입에 따라 적절한 툴 선택
        if state.analysis_type == "detailed":
            # 상세 분석 툴 사용
            response = await exaone_detailed_analyzer.ainvoke({
                "email_subject": state.email_subject,
                "email_content": state.email_content,
                "koelectra_result": state.koelectra_result
            })
        else:
            # 빠른 판정 툴 사용
            email_text = f"{state.email_subject} {state.email_content}"
            confidence = state.koelectra_result.get("confidence", 0.0)
            response = await exaone_quick_verdict.ainvoke({
                "email_text": email_text,
                "koelectra_confidence": confidence
            })

        state.exaone_response = response
        state.processing_steps.append("exaone_tool_analysis_completed")
        logger.info("EXAONE 툴 분석 완료")
        return state

    except Exception as e:
        logger.error(f"EXAONE 툴 분석 오류: {e}")
        state.error = f"EXAONE 툴 분석 오류: {str(e)}"
        return state

async def verdict_decision_node(state: VerdictState) -> VerdictState:
    """최종 판정 결정 노드"""
    try:
        logger.info("최종 판정 결정 시작")
        state.processing_steps.append("verdict_decision_started")

        if not state.exaone_response:
            state.error = "EXAONE 응답이 없습니다"
            return state

        # EXAONE 응답 분석
        response_lower = state.exaone_response.lower()

        if "스팸" in response_lower or "차단" in response_lower:
            state.final_verdict = "spam"
            state.confidence_adjustment = 0.1  # 신뢰도 상승
        elif "정상" in response_lower or "안전" in response_lower:
            state.final_verdict = "normal"
            state.confidence_adjustment = 0.1  # 신뢰도 상승
        elif "불확실" in response_lower or "보류" in response_lower:
            state.final_verdict = "uncertain"
            state.confidence_adjustment = 0.0  # 신뢰도 유지
        else:
            # 명확하지 않은 경우 KoELECTRA 결과 따름
            if state.koelectra_result.get("is_spam"):
                state.final_verdict = "spam"
            else:
                state.final_verdict = "normal"
            state.confidence_adjustment = 0.05  # 약간의 신뢰도 상승

        # 분석 요약 생성
        state.analysis_summary = f"EXAONE 판정: {state.final_verdict} (신뢰도 조정: +{state.confidence_adjustment:.2f})"

        state.processing_steps.append("verdict_decided")
        logger.info(f"최종 판정: {state.final_verdict}")
        return state

    except Exception as e:
        logger.error(f"판정 결정 오류: {e}")
        state.error = f"판정 결정 오류: {str(e)}"
        return state

async def finalize_verdict_node(state: VerdictState) -> VerdictState:
    """판정 결과 최종화 노드"""
    try:
        logger.info("판정 결과 최종화")
        state.processing_steps.append("verdict_finalized")
        state.end_time = datetime.now()

        # 처리 시간 계산
        if state.start_time and state.end_time:
            processing_time = (state.end_time - state.start_time).total_seconds()
            logger.info(f"EXAONE 판정 완료 - 처리시간: {processing_time:.2f}초")

        return state

    except Exception as e:
        logger.error(f"결과 최종화 오류: {e}")
        state.error = f"결과 최종화 오류: {str(e)}"
        return state

# 툴 실행 노드
async def tool_execution_node(state: VerdictState) -> VerdictState:
    """툴 실행 노드"""
    try:
        logger.info("툴 실행 노드 시작")
        state.processing_steps.append("tool_execution_started")

        # MCP 에이전트 래퍼 사용
        mcp_wrapper = get_mcp_agent_wrapper()

        result = await mcp_wrapper.analyze_with_exaone(
            email_subject=state.email_subject,
            email_content=state.email_content,
            koelectra_result=state.koelectra_result,
            analysis_type=state.analysis_type
        )

        # 결과를 상태에 반영
        state.exaone_response = result["exaone_response"]
        state.final_verdict = result["verdict"]
        state.confidence_adjustment = result["confidence_adjustment"]
        state.analysis_summary = result["analysis_summary"]

        state.processing_steps.append(f"tool_executed_{result['tool_used']}")
        logger.info("툴 실행 노드 완료")
        return state

    except Exception as e:
        logger.error(f"툴 실행 노드 오류: {e}")
        state.error = f"툴 실행 오류: {str(e)}"
        return state

# 워크플로우 구성
def create_verdict_workflow():
    """판독 에이전트 워크플로우 생성 (툴 기반)"""

    workflow = StateGraph(VerdictState)

    # 노드 추가
    workflow.add_node("initialize_analysis", initialize_analysis_node)
    workflow.add_node("generate_prompt", generate_prompt_node)
    workflow.add_node("tool_execution", tool_execution_node)  # 새로운 툴 실행 노드
    workflow.add_node("exaone_analysis", exaone_analysis_node)  # 기존 방식 유지
    workflow.add_node("verdict_decision", verdict_decision_node)
    workflow.add_node("finalize_verdict", finalize_verdict_node)

    # 엣지 연결 (툴 기반 워크플로우)
    workflow.set_entry_point("initialize_analysis")
    workflow.add_edge("initialize_analysis", "generate_prompt")
    workflow.add_edge("generate_prompt", "tool_execution")  # 툴 실행으로 변경
    workflow.add_edge("tool_execution", "finalize_verdict")  # 직접 최종화로
    workflow.add_edge("finalize_verdict", END)

    return workflow.compile()

def create_legacy_verdict_workflow():
    """기존 방식의 판독 에이전트 워크플로우 (호환성 유지)"""

    workflow = StateGraph(VerdictState)

    # 노드 추가
    workflow.add_node("initialize_analysis", initialize_analysis_node)
    workflow.add_node("generate_prompt", generate_prompt_node)
    workflow.add_node("exaone_analysis", exaone_analysis_node)
    workflow.add_node("verdict_decision", verdict_decision_node)
    workflow.add_node("finalize_verdict", finalize_verdict_node)

    # 엣지 연결 (기존 방식)
    workflow.set_entry_point("initialize_analysis")
    workflow.add_edge("initialize_analysis", "generate_prompt")
    workflow.add_edge("generate_prompt", "exaone_analysis")
    workflow.add_edge("exaone_analysis", "verdict_decision")
    workflow.add_edge("verdict_decision", "finalize_verdict")
    workflow.add_edge("finalize_verdict", END)

    return workflow.compile()

# 전역 워크플로우 인스턴스
_verdict_workflow = None

def get_verdict_workflow():
    """판독 워크플로우 인스턴스 가져오기"""
    global _verdict_workflow
    if _verdict_workflow is None:
        _verdict_workflow = create_verdict_workflow()
        logger.info("EXAONE 판독 워크플로우 생성 완료")
    return _verdict_workflow

# MCP 라우터용 간편 인터페이스
async def analyze_email_with_tools(
    email_subject: str,
    email_content: str,
    koelectra_result: Dict[str, Any]
) -> Dict[str, Any]:
    """
    툴 기반 이메일 판독 분석 (MCP 라우터용)

    Args:
        email_subject: 이메일 제목
        email_content: 이메일 내용
        koelectra_result: KoELECTRA 분석 결과

    Returns:
        판독 결과 딕셔너리
    """
    try:
        logger.info("툴 기반 EXAONE 이메일 판독 분석 시작")

        # MCP 에이전트 래퍼 직접 사용
        mcp_wrapper = get_mcp_agent_wrapper()

        # 분석 타입 결정
        confidence = koelectra_result.get("confidence", 0.0)
        analysis_type = "quick" if confidence > 0.8 else "detailed"

        # 툴 기반 분석 실행
        result = await mcp_wrapper.analyze_with_exaone(
            email_subject=email_subject,
            email_content=email_content,
            koelectra_result=koelectra_result,
            analysis_type=analysis_type
        )

        logger.info(f"툴 기반 EXAONE 판독 완료: {result['verdict']}")
        return result

    except Exception as e:
        logger.error(f"툴 기반 EXAONE 판독 분석 실패: {e}")
        raise

# 메인 판독 함수 (기존 워크플로우 방식)
async def analyze_email_verdict(
    email_subject: str,
    email_content: str,
    koelectra_result: Dict[str, Any]
) -> Dict[str, Any]:
    """
    이메일 판독 분석 메인 함수 (워크플로우 기반)

    Args:
        email_subject: 이메일 제목
        email_content: 이메일 내용
        koelectra_result: KoELECTRA 분석 결과

    Returns:
        판독 결과 딕셔너리
    """
    try:
        logger.info("워크플로우 기반 EXAONE 이메일 판독 분석 시작")

        # 초기 상태 생성
        initial_state = VerdictState(
            email_subject=email_subject,
            email_content=email_content,
            koelectra_result=koelectra_result,
            processing_steps=["verdict_analysis_started"]
        )

        # 워크플로우 실행 (툴 기반)
        workflow = get_verdict_workflow()
        final_state = await workflow.ainvoke(initial_state)

        # 오류 체크
        if final_state.error:
            raise Exception(final_state.error)

        # 결과 구성
        result = {
            "verdict": final_state.final_verdict,
            "confidence_adjustment": final_state.confidence_adjustment,
            "analysis_type": final_state.analysis_type,
            "analysis_summary": final_state.analysis_summary,
            "exaone_response": final_state.exaone_response,
            "processing_steps": final_state.processing_steps,
            "processing_time": (
                (final_state.end_time - final_state.start_time).total_seconds()
                if final_state.start_time and final_state.end_time else None
            )
        }

        logger.info(f"워크플로우 기반 EXAONE 판독 완료: {final_state.final_verdict}")
        return result

    except Exception as e:
        logger.error(f"워크플로우 기반 EXAONE 판독 분석 실패: {e}")
        raise

# 빠른 판정 함수 (간단한 케이스용)
async def quick_verdict(
    email_text: str,
    koelectra_confidence: float
) -> Dict[str, Any]:
    """빠른 판정 (고신뢰도 케이스용)"""
    try:
        logger.info("EXAONE 빠른 판정 시작")

        exaone_service = get_exaone_service()

        prompt = f"""
다음 이메일에 대한 빠른 스팸 판정을 해주세요.

이메일 내용: {email_text}
1차 AI 신뢰도: {koelectra_confidence:.3f}

간단히 다음 중 하나로 답변해주세요:
- 정상: 안전한 이메일
- 스팸: 스팸 메일
- 불확실: 추가 분석 필요

판정 근거를 2-3줄로 간단히 설명해주세요.
"""

        response = await exaone_service.generate_response(prompt)

        # 간단한 판정 분석
        response_lower = response.lower()
        if "스팸" in response_lower:
            verdict = "spam"
        elif "정상" in response_lower:
            verdict = "normal"
        else:
            verdict = "uncertain"

        result = {
            "verdict": verdict,
            "confidence_adjustment": 0.05,
            "analysis_type": "quick",
            "analysis_summary": f"빠른 판정: {verdict}",
            "exaone_response": response,
            "processing_steps": ["quick_verdict_completed"]
        }

        logger.info(f"EXAONE 빠른 판정 완료: {verdict}")
        return result

    except Exception as e:
        logger.error(f"EXAONE 빠른 판정 실패: {e}")
        raise

# 워크플로우 정보 조회
def get_workflow_info() -> Dict[str, Any]:
    """판독 에이전트 워크플로우 정보 반환"""
    return {
        "agent_name": "EXAONE Verdict Agent",
        "description": "EXAONE 기반 이메일 스팸 정밀 판독 에이전트",
        "workflow_steps": [
            "Initialize Analysis",
            "Generate Prompt",
            "EXAONE Analysis",
            "Verdict Decision",
            "Finalize Verdict"
        ],
        "analysis_types": {
            "detailed": "상세 분석 (신뢰도 ≤ 0.8)",
            "quick": "빠른 분석 (신뢰도 > 0.8)"
        },
        "verdict_options": ["spam", "normal", "uncertain"],
        "features": [
            "적응적 분석 타입 선택",
            "신뢰도 기반 프롬프트 생성",
            "상세 스팸 분석",
            "신뢰도 조정 기능"
        ]
    }


if __name__ == "__main__":
    # 테스트 코드
    import asyncio

    async def test_verdict_agent():
        try:
            # 테스트 데이터
            test_subject = "긴급! 계정 확인 필요"
            test_content = "보안상 문제로 계정 확인이 필요합니다. 아래 링크를 클릭하여 즉시 확인해주세요."
            koelectra_result = {
                "is_spam": True,
                "confidence": 0.75,
                "probabilities": {"정상": 0.25, "스팸": 0.75}
            }

            print("=== EXAONE 판독 에이전트 테스트 ===")

            # 상세 분석 테스트
            result = await analyze_email_verdict(
                test_subject, test_content, koelectra_result
            )

            print(f"판정 결과: {result['verdict']}")
            print(f"분석 타입: {result['analysis_type']}")
            print(f"신뢰도 조정: +{result['confidence_adjustment']}")
            print(f"처리 시간: {result['processing_time']:.2f}초")
            print(f"EXAONE 응답: {result['exaone_response'][:200]}...")

            # 빠른 판정 테스트
            print("\n=== 빠른 판정 테스트 ===")
            quick_result = await quick_verdict(
                f"{test_subject} {test_content}", 0.85
            )
            print(f"빠른 판정: {quick_result['verdict']}")
            print(f"응답: {quick_result['exaone_response'][:100]}...")

        except Exception as e:
            print(f"테스트 실패: {e}")
            import traceback
            traceback.print_exc()

    # 비동기 테스트 실행
    asyncio.run(test_verdict_agent())
