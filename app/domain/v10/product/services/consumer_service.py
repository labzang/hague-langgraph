"""소비자(Consumer) 규칙 기반 서비스."""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.domain.v10.product.bases.consumers import Consumer
from app.domain.v10.product.models.consumer_model import (
    ConsumerModel,
    ConsumerCreateModel,
    ConsumerUpdateModel,
)

logger = logging.getLogger(__name__)


class ConsumerService:
    """소비자 규칙 기반 서비스.

    규칙 기반 로직으로 소비자 CRUD 작업을 수행합니다.
    """

    def __init__(self):
        """ConsumerService 초기화."""
        # 데이터베이스 세션 생성
        engine = create_engine(settings.database_url)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        self.SessionLocal = SessionLocal
        logger.info("[서비스] ConsumerService 초기화 완료")

    def _get_session(self) -> Session:
        """데이터베이스 세션 반환."""
        return self.SessionLocal()

    async def create_consumer(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """소비자 생성 (규칙 기반).

        Args:
            data: 소비자 생성 데이터

        Returns:
            생성된 소비자 정보
        """
        logger.info(f"[서비스] 소비자 생성 - data: {data}")

        # 규칙 기반 검증
        if not data.get("name"):
            raise ValueError("이름은 필수입니다")
        if not data.get("email"):
            raise ValueError("이메일은 필수입니다")

        session = self._get_session()
        try:
            consumer = Consumer(
                name=data["name"],
                email=data["email"],
                phone=data.get("phone"),
                address=data.get("address"),
            )
            session.add(consumer)
            session.commit()
            session.refresh(consumer)

            result = ConsumerModel.model_validate(consumer).model_dump()
            logger.info(f"[서비스] 소비자 생성 완료 - id: {consumer.id}")
            return result
        except Exception as e:
            session.rollback()
            logger.error(f"[서비스] 소비자 생성 실패: {e}")
            raise
        finally:
            session.close()

    async def update_consumer(
        self,
        consumer_id: int,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """소비자 수정 (규칙 기반).

        Args:
            consumer_id: 소비자 ID
            data: 수정할 데이터

        Returns:
            수정된 소비자 정보
        """
        logger.info(f"[서비스] 소비자 수정 - id: {consumer_id}, data: {data}")

        session = self._get_session()
        try:
            consumer = session.query(Consumer).filter(Consumer.id == consumer_id).first()
            if not consumer:
                raise ValueError(f"소비자를 찾을 수 없습니다: {consumer_id}")

            # 규칙 기반 업데이트
            if "name" in data:
                consumer.name = data["name"]
            if "email" in data:
                consumer.email = data["email"]
            if "phone" in data:
                consumer.phone = data["phone"]
            if "address" in data:
                consumer.address = data["address"]

            session.commit()
            session.refresh(consumer)

            result = ConsumerModel.model_validate(consumer).model_dump()
            logger.info(f"[서비스] 소비자 수정 완료 - id: {consumer_id}")
            return result
        except Exception as e:
            session.rollback()
            logger.error(f"[서비스] 소비자 수정 실패: {e}")
            raise
        finally:
            session.close()

    async def get_consumer(self, consumer_id: int) -> Dict[str, Any]:
        """소비자 조회 (규칙 기반).

        Args:
            consumer_id: 소비자 ID

        Returns:
            소비자 정보
        """
        logger.info(f"[서비스] 소비자 조회 - id: {consumer_id}")

        session = self._get_session()
        try:
            consumer = session.query(Consumer).filter(Consumer.id == consumer_id).first()
            if not consumer:
                raise ValueError(f"소비자를 찾을 수 없습니다: {consumer_id}")

            result = ConsumerModel.model_validate(consumer).model_dump()
            return result
        except Exception as e:
            logger.error(f"[서비스] 소비자 조회 실패: {e}")
            raise
        finally:
            session.close()

    async def list_consumers(
        self,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """소비자 목록 조회 (규칙 기반).

        Args:
            limit: 조회할 개수
            offset: 시작 위치

        Returns:
            소비자 목록
        """
        logger.info(f"[서비스] 소비자 목록 조회 - limit: {limit}, offset: {offset}")

        session = self._get_session()
        try:
            consumers = session.query(Consumer).offset(offset).limit(limit).all()
            result = [ConsumerModel.model_validate(c).model_dump() for c in consumers]
            return result
        except Exception as e:
            logger.error(f"[서비스] 소비자 목록 조회 실패: {e}")
            raise
        finally:
            session.close()

    async def delete_consumer(self, consumer_id: int) -> Dict[str, Any]:
        """소비자 삭제 (규칙 기반).

        Args:
            consumer_id: 소비자 ID

        Returns:
            삭제 결과
        """
        logger.info(f"[서비스] 소비자 삭제 - id: {consumer_id}")

        session = self._get_session()
        try:
            consumer = session.query(Consumer).filter(Consumer.id == consumer_id).first()
            if not consumer:
                raise ValueError(f"소비자를 찾을 수 없습니다: {consumer_id}")

            session.delete(consumer)
            session.commit()

            logger.info(f"[서비스] 소비자 삭제 완료 - id: {consumer_id}")
            return {"status": "success", "message": f"소비자 {consumer_id}가 삭제되었습니다"}
        except Exception as e:
            session.rollback()
            logger.error(f"[서비스] 소비자 삭제 실패: {e}")
            raise
        finally:
            session.close()

