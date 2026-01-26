"""주문(Order) Pydantic 모델."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.domain.v10.product.bases.orders import OrderStatus


class OrderModel(BaseModel):
    """주문 정보를 전송하기 위한 Pydantic 모델.

    SQLAlchemy Order 모델의 transfer 객체입니다.
    """

    id: Optional[int] = Field(None, description="주문 고유 식별자")
    consumer_id: int = Field(..., description="소비자 ID", gt=0)
    product_id: int = Field(..., description="상품 ID", gt=0)
    quantity: int = Field(..., description="주문 수량", gt=0)
    unit_price: int = Field(..., description="단가 (주문 시점의 가격)", ge=0)
    total_price: int = Field(..., description="총 가격 (quantity * unit_price)", ge=0)
    status: OrderStatus = Field(..., description="주문 상태")
    order_date: Optional[datetime] = Field(None, description="주문 일시")
    created_at: Optional[datetime] = Field(None, description="생성 일시")
    updated_at: Optional[datetime] = Field(None, description="수정 일시")

    class Config:
        """Pydantic 설정."""

        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class OrderCreateModel(BaseModel):
    """주문 생성 요청 모델."""

    consumer_id: int = Field(..., description="소비자 ID", gt=0)
    product_id: int = Field(..., description="상품 ID", gt=0)
    quantity: int = Field(1, description="주문 수량", gt=0)
    unit_price: int = Field(..., description="단가 (주문 시점의 가격)", ge=0)
    total_price: int = Field(..., description="총 가격 (quantity * unit_price)", ge=0)
    status: OrderStatus = Field(OrderStatus.PENDING, description="주문 상태")


class OrderUpdateModel(BaseModel):
    """주문 수정 요청 모델."""

    quantity: Optional[int] = Field(None, description="주문 수량", gt=0)
    unit_price: Optional[int] = Field(None, description="단가", ge=0)
    total_price: Optional[int] = Field(None, description="총 가격", ge=0)
    status: Optional[OrderStatus] = Field(None, description="주문 상태")


class OrderDetailModel(OrderModel):
    """주문 상세 정보 모델 (관계 포함)."""

    consumer_name: Optional[str] = Field(None, description="소비자 이름")
    consumer_email: Optional[str] = Field(None, description="소비자 이메일")
    product_name: Optional[str] = Field(None, description="상품명")
    product_price: Optional[int] = Field(None, description="상품 현재 가격")

