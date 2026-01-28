"""챗팅 질문 처리 API 라우터.

사용자 질문을 받아서 ChatOrchestrator로 전달합니다.
"""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.domain.v10.soccer.hub.orchestrators.chat_orchestrator import ChatOrchestrator

router = APIRouter()
logger = logging.getLogger(__name__)

# 오케스트레이터 인스턴스 (싱글톤 패턴)
_orchestrator: Optional[ChatOrchestrator] = None


def get_orchestrator() -> ChatOrchestrator:
    """ChatOrchestrator 싱글톤 인스턴스를 반환합니다.

    Returns:
        ChatOrchestrator 인스턴스
    """
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = ChatOrchestrator()
    return _orchestrator


class QueryRequest(BaseModel):
    """질문 요청 모델"""
    question: str


@router.post("/query")
async def process_query(request: QueryRequest) -> JSONResponse:
    """사용자 질문을 처리합니다.

    Args:
        request: 질문 요청 객체

    Returns:
        처리 결과

    Raises:
        HTTPException: 처리 중 오류 발생 시
    """
    logger.info(f"[챗팅 라우터] 질문 수신: {request.question}")
    print(f"[chat_router] 사용자 질문: {request.question}")

    try:
        orchestrator = get_orchestrator()
        result = await orchestrator.process_query(request.question)
        logger.info("[챗팅 라우터] 오케스트레이터 처리 완료")

        response_data = {
            "success": True,
            "question": request.question,
            "result": result
        }

        logger.info(f"[챗팅 라우터] 응답 준비 완료")
        return JSONResponse(
            status_code=200,
            content=response_data
        )
    except Exception as e:
        logger.error(f"[챗팅 라우터 오류] {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"질문 처리 중 오류 발생: {str(e)}"
        )

