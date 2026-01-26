"""상품(Product) API 라우터."""

import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
import json

from app.domain.v10.product.models.product_model import (
    ProductModel,
    ProductCreateModel,
    ProductUpdateModel,
)
from app.domain.v10.product.orchestrators.product_flow import ProductFlow

router = APIRouter()
logger = logging.getLogger(__name__)


class ProductRequest(BaseModel):
    """상품 요청 모델."""
    action: str  # "create", "update", "get", "list", "delete", "recommend"
    data: Optional[dict] = None
    product_id: Optional[int] = None
    use_policy: bool = False  # True: 정책 기반, False: 규칙 기반


@router.post("/", response_model=dict)
async def handle_product_request(request: ProductRequest):
    """상품 요청 처리 엔드포인트.

    규칙 기반 또는 정책 기반으로 요청을 처리합니다.
    """
    try:
        flow = ProductFlow()
        result = await flow.process_request(
            action=request.action,
            data=request.data or {},
            product_id=request.product_id,
            use_policy=request.use_policy
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/create", response_model=ProductModel)
async def create_product(product: ProductCreateModel, use_policy: bool = False):
    """상품 생성."""
    try:
        flow = ProductFlow()
        result = await flow.process_request(
            action="create",
            data=product.model_dump(),
            use_policy=use_policy
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{product_id}", response_model=ProductModel)
async def get_product(product_id: int, use_policy: bool = False):
    """상품 조회."""
    try:
        flow = ProductFlow()
        result = await flow.process_request(
            action="get",
            product_id=product_id,
            use_policy=use_policy
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{product_id}", response_model=ProductModel)
async def update_product(
    product_id: int,
    product: ProductUpdateModel,
    use_policy: bool = False
):
    """상품 수정."""
    try:
        flow = ProductFlow()
        result = await flow.process_request(
            action="update",
            data=product.model_dump(exclude_unset=True),
            product_id=product_id,
            use_policy=use_policy
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=List[ProductModel])
async def list_products(use_policy: bool = False, limit: int = 100, offset: int = 0):
    """상품 목록 조회."""
    try:
        flow = ProductFlow()
        result = await flow.process_request(
            action="list",
            data={"limit": limit, "offset": offset},
            use_policy=use_policy
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{product_id}", response_model=dict)
async def delete_product(product_id: int, use_policy: bool = False):
    """상품 삭제."""
    try:
        flow = ProductFlow()
        result = await flow.process_request(
            action="delete",
            product_id=product_id,
            use_policy=use_policy
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recommend", response_model=dict)
async def recommend_products(
    request: Request,
    use_policy: bool = False
):
    """상품 추천.

    Args:
        request: FastAPI Request 객체 (JSON body를 받기 위함)
        use_policy: True면 정책 기반(Agent), False면 규칙 기반(Service)
    """
    try:
        # Request body를 JSON으로 파싱
        body = await request.json()

        # 전송된 메시지 프린트 및 로깅
        message = body.get("message", "") if body else ""
        print("=" * 60)
        print(f"[상품추천 요청] 전송된 메시지: {message}")
        print(f"[상품추천 요청] 전체 데이터: {json.dumps(body, ensure_ascii=False, indent=2)}")
        print("=" * 60)

        logger.info("=" * 60)
        logger.info(f"[상품추천 요청] 전송된 메시지: {message}")
        logger.info(f"[상품추천 요청] 전체 데이터: {body}")
        logger.info("=" * 60)

        # sys.stdout에 강제로 flush하여 즉시 출력
        import sys
        sys.stdout.flush()

        flow = ProductFlow()
        result = await flow.process_request(
            action="recommend",
            data=body or {},
            use_policy=use_policy
        )
        return result
    except json.JSONDecodeError as e:
        logger.error(f"[오류] JSON 파싱 실패: {e}")
        raise HTTPException(status_code=400, detail=f"잘못된 JSON 형식: {str(e)}")
    except Exception as e:
        logger.error(f"[오류] 상품추천 처리 실패: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

