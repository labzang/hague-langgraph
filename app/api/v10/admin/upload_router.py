"""파일 업로드 API 라우터.

JSONL 파일을 multipart/form-data로 받아서 처리합니다.
"""
import json
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse

router = APIRouter()


@router.post("/upload")
async def upload_jsonl_file(
    file: UploadFile = File(..., description="업로드할 JSONL 파일"),
    item_type: str = Form(default="jsonl", description="아이템 타입"),
) -> JSONResponse:
    """JSONL 파일을 업로드하고 처리합니다.

    Args:
        file: 업로드할 JSONL 파일 (multipart/form-data)
        item_type: 아이템 타입 (기본값: "jsonl")

    Returns:
        업로드 결과 및 처리된 아이템 수

    Raises:
        HTTPException: 파일 형식이 올바르지 않거나 처리 중 오류 발생 시
    """
    # 파일 확장자 검증
    if not file.filename or not file.filename.endswith('.jsonl'):
        raise HTTPException(
            status_code=400,
            detail="JSONL 파일만 업로드 가능합니다. (.jsonl 확장자 필요)"
        )

    try:
        # 파일 내용 읽기
        contents = await file.read()
        text_content = contents.decode('utf-8')

        # JSONL 파싱 (각 줄이 JSON 객체)
        items = []
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

        # TODO: 실제 데이터 처리 로직 구현
        # 예: 데이터베이스에 저장, 벡터 스토어에 추가 등
        # processed_count = await process_items(items, item_type)

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "파일이 성공적으로 업로드되었습니다.",
                "filename": file.filename,
                "item_type": item_type,
                "item_count": len(items),
                "file_size": len(contents),
                # "processed_count": processed_count,
            }
        )

    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400,
            detail="파일 인코딩 오류: UTF-8 형식의 파일만 지원합니다."
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"파일 처리 중 오류 발생: {str(e)}"
        )


@router.get("/upload/status")
async def get_upload_status() -> JSONResponse:
    """업로드 상태를 확인합니다.

    Returns:
        업로드 통계 정보
    """
    # TODO: 실제 업로드 통계 구현
    return JSONResponse(
        status_code=200,
        content={
            "total_uploads": 0,
            "successful_uploads": 0,
            "failed_uploads": 0,
        }
    )

