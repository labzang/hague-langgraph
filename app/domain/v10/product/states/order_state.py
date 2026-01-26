"""주문(Order) 상태 머신."""

from enum import Enum
from typing import Optional, Set
from datetime import datetime

from pydantic import BaseModel, Field

from app.domain.v10.product.bases.orders import OrderStatus


class OrderState(BaseModel):
    """주문 상태 머신 클래스.

    주문의 상태를 관리하고 상태 전이를 검증합니다.
    """

    status: OrderStatus = Field(
        default=OrderStatus.PENDING,
        description="주문 상태"
    )
    last_status_change: Optional[datetime] = Field(
        None,
        description="마지막 상태 변경 일시"
    )
    status_history: list[dict] = Field(
        default_factory=list,
        description="상태 변경 이력"
    )

    # 상태 전이 규칙
    _valid_transitions: dict[OrderStatus, Set[OrderStatus]] = {
        OrderStatus.PENDING: {
            OrderStatus.CONFIRMED,
            OrderStatus.CANCELLED
        },
        OrderStatus.CONFIRMED: {
            OrderStatus.PROCESSING,
            OrderStatus.CANCELLED
        },
        OrderStatus.PROCESSING: {
            OrderStatus.SHIPPED,
            OrderStatus.CANCELLED
        },
        OrderStatus.SHIPPED: {
            OrderStatus.DELIVERED,
            OrderStatus.CANCELLED  # 배송 중 취소는 특수 케이스
        },
        OrderStatus.DELIVERED: set(),  # 배송 완료 후 전이 불가
        OrderStatus.CANCELLED: set()  # 취소 후 전이 불가
    }

    def can_transition_to(self, new_status: OrderStatus) -> bool:
        """상태 전이가 가능한지 확인.

        Args:
            new_status: 전이하려는 새로운 상태

        Returns:
            전이 가능 여부
        """
        if new_status == self.status:
            return True  # 같은 상태로의 전이는 허용

        allowed_transitions = self._valid_transitions.get(self.status, set())
        return new_status in allowed_transitions

    def transition_to(self, new_status: OrderStatus, reason: Optional[str] = None) -> bool:
        """상태를 전이.

        Args:
            new_status: 전이하려는 새로운 상태
            reason: 상태 변경 사유

        Returns:
            전이 성공 여부

        Raises:
            ValueError: 유효하지 않은 상태 전이인 경우
        """
        if not self.can_transition_to(new_status):
            raise ValueError(
                f"상태 전이 불가: {self.status.value} -> {new_status.value}"
            )

        # 상태 이력 기록
        self.status_history.append({
            "from_status": self.status.value,
            "to_status": new_status.value,
            "timestamp": datetime.now().isoformat(),
            "reason": reason
        })

        self.status = new_status
        self.last_status_change = datetime.now()
        return True

    def is_completed(self) -> bool:
        """완료 상태인지 확인 (배송 완료 또는 취소)."""
        return self.status in {OrderStatus.DELIVERED, OrderStatus.CANCELLED}

    def is_cancellable(self) -> bool:
        """취소 가능한 상태인지 확인."""
        return self.status not in {OrderStatus.DELIVERED, OrderStatus.CANCELLED}

    def is_shippable(self) -> bool:
        """배송 가능한 상태인지 확인."""
        return self.status == OrderStatus.PROCESSING

    class Config:
        """Pydantic 설정."""

        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

