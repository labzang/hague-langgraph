"""소비자(Consumer) API 라우터."""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from app.domain.v10.product.models.consumer_model import (
    ConsumerModel,
    ConsumerCreateModel,
    ConsumerUpdateModel,
)
from app.domain.v10.product.orchestrators.consumer_flow import ConsumerFlow

router = APIRouter()


class ConsumerRequest(BaseModel):
    """소비자 요청 모델."""
    action: str  # "create", "update", "get", "list", "delete"
    data: Optional[dict] = None
    consumer_id: Optional[int] = None
    use_policy: bool = False  # True: 정책 기반, False: 규칙 기반


@router.post("/", response_model=dict)
async def handle_consumer_request(request: ConsumerRequest):
    """소비자 요청 처리 엔드포인트.

    규칙 기반 또는 정책 기반으로 요청을 처리합니다.
    """
    try:
        flow = ConsumerFlow()
        result = await flow.process_request(
            action=request.action,
            data=request.data or {},
            consumer_id=request.consumer_id,
            use_policy=request.use_policy
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/create", response_model=ConsumerModel)
async def create_consumer(consumer: ConsumerCreateModel, use_policy: bool = False):
    """소비자 생성."""
    try:
        flow = ConsumerFlow()
        result = await flow.process_request(
            action="create",
            data=consumer.model_dump(),
            use_policy=use_policy
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{consumer_id}", response_model=ConsumerModel)
async def get_consumer(consumer_id: int, use_policy: bool = False):
    """소비자 조회."""
    try:
        flow = ConsumerFlow()
        result = await flow.process_request(
            action="get",
            consumer_id=consumer_id,
            use_policy=use_policy
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{consumer_id}", response_model=ConsumerModel)
async def update_consumer(
    consumer_id: int,
    consumer: ConsumerUpdateModel,
    use_policy: bool = False
):
    """소비자 수정."""
    try:
        flow = ConsumerFlow()
        result = await flow.process_request(
            action="update",
            data=consumer.model_dump(exclude_unset=True),
            consumer_id=consumer_id,
            use_policy=use_policy
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=List[ConsumerModel])
async def list_consumers(use_policy: bool = False, limit: int = 100, offset: int = 0):
    """소비자 목록 조회."""
    try:
        flow = ConsumerFlow()
        result = await flow.process_request(
            action="list",
            data={"limit": limit, "offset": offset},
            use_policy=use_policy
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{consumer_id}", response_model=dict)
async def delete_consumer(consumer_id: int, use_policy: bool = False):
    """소비자 삭제."""
    try:
        flow = ConsumerFlow()
        result = await flow.process_request(
            action="delete",
            consumer_id=consumer_id,
            use_policy=use_policy
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

