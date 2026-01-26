"""소비자(Consumer) 정책 기반 에이전트.

Fine-tuned 어댑터를 사용하여 정책 기반 처리를 수행합니다.
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional

try:
    import torch
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        BitsAndBytesConfig,
    )
    from peft import PeftModel
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    logging.warning("transformers 또는 peft가 설치되지 않았습니다.")

from app.domain.v10.product.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class ConsumerAgent(BaseAgent):
    """소비자 정책 기반 에이전트.

    Fine-tuned 어댑터를 사용하여 정책 기반 의사결정을 수행합니다.
    """

    def __init__(
        self,
        adapter_path: Optional[Path] = None,
        base_model_name: str = "beomi/llama-2-ko-7b",
        name: str = "ConsumerAgent",
        instruction: str = "소비자 관련 작업을 정책 기반으로 처리합니다."
    ):
        """ConsumerAgent 초기화.

        Args:
            adapter_path: Fine-tuned 어댑터 경로
            base_model_name: 베이스 모델 이름
            name: 에이전트 이름
            instruction: 에이전트 지시사항
        """
        super().__init__(name=name, instruction=instruction)
        self.adapter_path = adapter_path
        self.base_model_name = base_model_name
        self.model = None
        self.tokenizer = None

        if TRANSFORMERS_AVAILABLE and adapter_path:
            self._load_model()
        else:
            logger.warning("[에이전트] 모델 로드 스킵 (어댑터 경로 없음 또는 패키지 미설치)")

    def _load_model(self):
        """Fine-tuned 어댑터 모델 로드."""
        try:
            if not self.adapter_path or not self.adapter_path.exists():
                logger.warning(f"[에이전트] 어댑터 경로가 유효하지 않습니다: {self.adapter_path}")
                return

            logger.info(f"[에이전트] 모델 로딩 시작 - base: {self.base_model_name}, adapter: {self.adapter_path}")

            # 토크나이저 로드
            self.tokenizer = AutoTokenizer.from_pretrained(self.base_model_name)
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token

            # 베이스 모델 로드
            device_map = "auto" if torch.cuda.is_available() else "cpu"

            if torch.cuda.is_available():
                quantization_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.float16,
                    bnb_4bit_use_double_quant=True,
                    bnb_4bit_quant_type="nf4"
                )
                base_model = AutoModelForCausalLM.from_pretrained(
                    self.base_model_name,
                    quantization_config=quantization_config,
                    device_map=device_map,
                    torch_dtype=torch.float16,
                )
            else:
                base_model = AutoModelForCausalLM.from_pretrained(
                    self.base_model_name,
                    device_map=device_map,
                    torch_dtype=torch.float32,
                )

            # LoRA 어댑터 로드
            self.model = PeftModel.from_pretrained(base_model, str(self.adapter_path))
            self.model.eval()

            logger.info("[에이전트] 모델 로딩 완료")
        except Exception as e:
            logger.error(f"[에이전트] 모델 로딩 실패: {e}")
            self.model = None
            self.tokenizer = None

    async def execute(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """에이전트 실행 로직.

        Args:
            task: 실행할 작업 설명
            context: 실행 컨텍스트 (action, data, consumer_id 등)

        Returns:
            실행 결과
        """
        logger.info(f"[에이전트] 작업 실행 - task: {task}, context: {context}")

        action = context.get("action", "unknown")
        data = context.get("data", {})
        consumer_id = context.get("consumer_id")

        # 모델이 로드되지 않은 경우 기본 응답
        if self.model is None or self.tokenizer is None:
            logger.warning("[에이전트] 모델이 로드되지 않아 기본 로직으로 처리")
            return await self._fallback_execute(action, data, consumer_id)

        # 정책 기반 처리 (모델 사용)
        try:
            # 프롬프트 생성
            prompt = self._create_prompt(action, data, consumer_id)

            # 모델 추론
            inputs = self.tokenizer(
                prompt,
                return_tensors="pt",
                truncation=True,
                max_length=512
            )

            if torch.cuda.is_available():
                inputs = {k: v.to(self.model.device) for k, v in inputs.items()}

            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=256,
                    temperature=0.7,
                    do_sample=True,
                    pad_token_id=self.tokenizer.pad_token_id
                )

            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)

            # 응답 파싱 및 결과 생성
            result = self._parse_response(action, response, data, consumer_id)

            logger.info(f"[에이전트] 작업 완료 - action: {action}")
            return result

        except Exception as e:
            logger.error(f"[에이전트] 모델 실행 실패: {e}")
            # 폴백 처리
            return await self._fallback_execute(action, data, consumer_id)

    def _create_prompt(self, action: str, data: Dict[str, Any], consumer_id: Optional[int]) -> str:
        """작업에 맞는 프롬프트 생성."""
        base_prompt = f"""소비자 관리 시스템에서 다음 작업을 수행하세요:

작업: {action}
"""

        if consumer_id:
            base_prompt += f"소비자 ID: {consumer_id}\n"

        if data:
            base_prompt += f"데이터: {data}\n"

        base_prompt += "\n적절한 처리를 수행하고 결과를 반환하세요."

        return base_prompt

    def _parse_response(
        self,
        action: str,
        response: str,
        data: Dict[str, Any],
        consumer_id: Optional[int]
    ) -> Dict[str, Any]:
        """모델 응답을 파싱하여 결과 생성."""
        # 실제 구현에서는 응답을 파싱하여 구조화된 결과를 반환
        # 여기서는 간단한 예시로 처리
        return {
            "status": "success",
            "action": action,
            "consumer_id": consumer_id,
            "message": "정책 기반 처리 완료",
            "response": response,
            "data": data
        }

    async def _fallback_execute(
        self,
        action: str,
        data: Dict[str, Any],
        consumer_id: Optional[int]
    ) -> Dict[str, Any]:
        """모델이 없을 때 기본 처리."""
        logger.info(f"[에이전트] 폴백 처리 - action: {action}")

        return {
            "status": "success",
            "action": action,
            "consumer_id": consumer_id,
            "message": "기본 처리 완료 (모델 미사용)",
            "data": data
        }

