"""상품(Product) 오케스트레이터 플로우.

규칙 기반과 정책 기반 처리를 분기합니다.
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional

from app.domain.v10.product.services.product_service import ProductService
from app.domain.v10.product.agents.product_agent import ProductAgent

logger = logging.getLogger(__name__)


class ProductFlow:
    """상품 처리 플로우 오케스트레이터.

    규칙 기반(Service)과 정책 기반(Agent) 처리를 분기합니다.
    """

    def __init__(self):
        """ProductFlow 초기화."""
        self.service = None
        self.agent = None
        self.adapter_path = None
        self._load_adapter()

    def _load_adapter(self):
        """Fine-tuned 어댑터 로드."""
        try:
            # 프로젝트 루트 기준으로 어댑터 경로 설정
            project_root = Path(__file__).parent.parent.parent.parent.parent
            adapter_base_path = project_root / "artifacts" / "fine-tuned-adapters" / "product-service"

            # product-service 어댑터 경로 찾기
            if adapter_base_path.exists():
                # 가장 최근 실행 디렉토리 찾기
                lora_path = adapter_base_path / "product_service" / "lora"
                if lora_path.exists():
                    # run_* 디렉토리 중 가장 최근 것 찾기
                    run_dirs = sorted(
                        [d for d in lora_path.iterdir() if d.is_dir() and d.name.startswith("run_")],
                        key=lambda x: x.stat().st_mtime,
                        reverse=True
                    )
                    if run_dirs:
                        self.adapter_path = run_dirs[0]
                        logger.info(f"[어댑터] Product Service 어댑터 경로: {self.adapter_path}")
                    else:
                        # fixed_model 또는 manual_adapter 사용
                        fixed_model = lora_path / "fixed_model"
                        if fixed_model.exists():
                            self.adapter_path = fixed_model
                            logger.info(f"[어댑터] Fixed Model 어댑터 경로: {self.adapter_path}")
                else:
                    logger.warning(f"[경고] LoRA 경로를 찾을 수 없습니다: {lora_path}")
            else:
                logger.warning(f"[경고] 어댑터 베이스 경로를 찾을 수 없습니다: {adapter_base_path}")
        except Exception as e:
            logger.error(f"[오류] 어댑터 로드 실패: {e}")

    async def process_request(
        self,
        action: str,
        data: Optional[Dict[str, Any]] = None,
        product_id: Optional[int] = None,
        use_policy: bool = False
    ) -> Dict[str, Any]:
        """요청을 처리합니다.

        Args:
            action: 수행할 액션 (create, update, get, list, delete, recommend)
            data: 요청 데이터
            product_id: 상품 ID
            use_policy: True면 정책 기반(Agent), False면 규칙 기반(Service)

        Returns:
            처리 결과
        """
        logger.info(f"[플로우] 요청 처리 시작 - action: {action}, use_policy: {use_policy}")

        if use_policy:
            # 정책 기반 처리 (Agent)
            return await self._process_with_agent(action, data, product_id)
        else:
            # 규칙 기반 처리 (Service)
            return await self._process_with_service(action, data, product_id)

    async def _process_with_service(
        self,
        action: str,
        data: Optional[Dict[str, Any]],
        product_id: Optional[int]
    ) -> Dict[str, Any]:
        """규칙 기반 서비스로 처리."""
        logger.info(f"[서비스] 규칙 기반 처리 - action: {action}")

        if self.service is None:
            self.service = ProductService()

        try:
            if action == "create":
                return await self.service.create_product(data or {})
            elif action == "update":
                if product_id is None:
                    raise ValueError("product_id가 필요합니다")
                return await self.service.update_product(product_id, data or {})
            elif action == "get":
                if product_id is None:
                    raise ValueError("product_id가 필요합니다")
                return await self.service.get_product(product_id)
            elif action == "list":
                limit = data.get("limit", 100) if data else 100
                offset = data.get("offset", 0) if data else 0
                return await self.service.list_products(limit=limit, offset=offset)
            elif action == "delete":
                if product_id is None:
                    raise ValueError("product_id가 필요합니다")
                return await self.service.delete_product(product_id)
            elif action == "recommend":
                return await self.service.recommend_products(data or {})
            else:
                raise ValueError(f"지원하지 않는 액션: {action}")
        except Exception as e:
            logger.error(f"[서비스] 처리 실패: {e}")
            raise

    async def _process_with_agent(
        self,
        action: str,
        data: Optional[Dict[str, Any]],
        product_id: Optional[int]
    ) -> Dict[str, Any]:
        """정책 기반 에이전트로 처리."""
        logger.info(f"[에이전트] 정책 기반 처리 - action: {action}")

        if self.agent is None:
            self.agent = ProductAgent(adapter_path=self.adapter_path)

        try:
            # 에이전트에 컨텍스트 전달
            context = {
                "action": action,
                "data": data or {},
                "product_id": product_id,
            }

            task = f"상품 {action} 작업을 수행하세요"
            result = await self.agent.execute(task, context)
            return result
        except Exception as e:
            logger.error(f"[에이전트] 처리 실패: {e}")
            raise

