"""선수 데이터 업로드 API 라우터.

JSONL 파일을 multipart/form-data로 받아서 처리합니다.
"""
import json
import logging
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse

from app.domain.v10.soccer.hub.orchestrators.player_orchestrator import PlayerOrchestrator

router = APIRouter()
logger = logging.getLogger(__name__)

# 오케스트레이터 인스턴스 (싱글톤 패턴)
_orchestrator: Optional[PlayerOrchestrator] = None


def get_orchestrator() -> PlayerOrchestrator:
    """PlayerOrchestrator 싱글톤 인스턴스를 반환합니다.

    Returns:
        PlayerOrchestrator 인스턴스
    """
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = PlayerOrchestrator()
    return _orchestrator


@router.post("/upload")
async def upload_player_jsonl(
    file: UploadFile = File(..., description="업로드할 선수 JSONL 파일"),
) -> JSONResponse:
    """선수 JSONL 파일을 업로드하고 첫 5개 행을 출력합니다.

    Args:
        file: 업로드할 JSONL 파일 (multipart/form-data)

    Returns:
        업로드 결과 및 첫 5개 행 데이터

    Raises:
        HTTPException: 파일 형식이 올바르지 않거나 처리 중 오류 발생 시
    """
    logger.info(f"[선수 업로드 시작] 파일명: {file.filename if file.filename else 'Unknown'}")

    # 파일 확장자 검증
    if not file.filename or not file.filename.endswith('.jsonl'):
        logger.warning(f"[선수 업로드 실패] 잘못된 파일 형식: {file.filename}")
        raise HTTPException(
            status_code=400,
            detail="JSONL 파일만 업로드 가능합니다. (.jsonl 확장자 필요)"
        )

    try:
        # 파일 내용 읽기
        logger.info("[선수 업로드] 파일 읽기 시작...")
        contents = await file.read()
        logger.info(f"[선수 업로드] 파일 크기: {len(contents)} bytes")
        text_content = contents.decode('utf-8')
        logger.info("[선수 업로드] 파일 디코딩 완료")

        # JSONL 파싱 (각 줄이 JSON 객체)
        items: List[Dict[str, Any]] = []
        lines = text_content.strip().split('\n')

        for line_num, line in enumerate(lines, start=1):
            line = line.strip()
            if not line:
                continue

            try:
                item = json.loads(line)
                items.append(item)
            except json.JSONDecodeError as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"파일의 {line_num}번째 줄에서 JSON 파싱 오류: {str(e)}"
                )

        # 첫 5개 행만 추출 (로그용)
        first_five_items = items[:5]

        # 로그 출력
        logger.info(f"[선수 업로드 성공] 파일명: {file.filename}, 총 {len(items)}개 항목")
        logger.info(f"[선수 업로드] 첫 5개 행 출력:")
        for idx, item in enumerate(first_five_items, start=1):
            logger.info(f"  [{idx}] {json.dumps(item, ensure_ascii=False, indent=2)}")

        # 오케스트레이터를 통해 처리
        logger.info("[선수 업로드] 오케스트레이터로 처리 시작...")
        orchestrator = get_orchestrator()
        processing_result = await orchestrator.process_players(items)

        response_data = {
            "success": True,
            "message": "파일이 성공적으로 업로드되고 처리되었습니다.",
            "filename": file.filename,
            "total_items": len(items),
            "first_five_items": first_five_items,
            "file_size": len(contents),
            "processing_result": processing_result,
        }

        logger.info(f"[선수 업로드] 응답 준비 완료")
        return JSONResponse(
            status_code=200,
            content=response_data
        )

    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400,
            detail="파일 인코딩 오류: UTF-8 형식의 파일만 지원합니다."
        )
    except Exception as e:
        logger.error(f"[선수 업로드 오류] {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"파일 처리 중 오류 발생: {str(e)}"
        )

