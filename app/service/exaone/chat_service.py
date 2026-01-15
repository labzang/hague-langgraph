"""
EXAONE 기반 정밀 스팸 분석 서비스
"""

import asyncio
import logging
from typing import Optional, Dict, Any
from pathlib import Path

from app.service.chat_service import QLoRAChatService

logger = logging.getLogger(__name__)

class ExaoneService:
    """EXAONE 기반 정밀 스팸 분석 서비스"""

    def __init__(
        self,
        model_path: str = "app/model/exaone-2.4b",
        adapter_path: Optional[str] = None,
        max_new_tokens: int = 512,
        temperature: float = 0.3  # 분석용이므로 낮은 온도
    ):
        """
        Args:
            model_path: EXAONE 모델 경로
            adapter_path: LoRA 어댑터 경로 (있는 경우)
            max_new_tokens: 최대 생성 토큰 수
            temperature: 생성 온도 (분석용이므로 낮게 설정)
        """
        self.model_path = model_path
        self.adapter_path = adapter_path
        self.max_new_tokens = max_new_tokens
        self.temperature = temperature

        # QLoRA 채팅 서비스 초기화
        self.chat_service = None
        self._initialize_service()

        logger.info("EXAONE 서비스 초기화 완료")

    def _initialize_service(self):
        """EXAONE 채팅 서비스 초기화"""
        try:
            self.chat_service = QLoRAChatService(
                model_name_or_path=self.model_path,
                adapter_path=self.adapter_path,
                use_4bit=True,  # 메모리 효율성을 위해 4bit 양자화 사용
                lora_r=64,
                lora_alpha=16,
                target_modules=["q_proj", "k_proj", "v_proj", "o_proj"]
            )
            logger.info(f"EXAONE 모델 로드 완료: {self.model_path}")

        except Exception as e:
            logger.error(f"EXAONE 서비스 초기화 실패: {e}")
            raise

    async def generate_response(self, prompt: str) -> str:
        """비동기 응답 생성"""
        try:
            # CPU 집약적 작업을 별도 스레드에서 실행
            response = await asyncio.to_thread(
                self._generate_sync,
                prompt
            )
            return response

        except Exception as e:
            logger.error(f"EXAONE 응답 생성 실패: {e}")
            raise

    def _generate_sync(self, prompt: str) -> str:
        """동기 응답 생성"""
        if self.chat_service is None:
            raise RuntimeError("EXAONE 서비스가 초기화되지 않았습니다")

        try:
            response = self.chat_service.chat(
                message=prompt,
                max_new_tokens=self.max_new_tokens,
                temperature=self.temperature,
                top_p=0.9,
                do_sample=True
            )

            return response.strip()

        except Exception as e:
            logger.error(f"EXAONE 동기 생성 실패: {e}")
            raise

    async def analyze_spam_detailed(
        self,
        email_subject: str,
        email_content: str,
        koelectra_result: Dict[str, Any]
    ) -> str:
        """상세 스팸 분석"""

        # 분석용 프롬프트 구성
        prompt = f"""
당신은 이메일 보안 전문가입니다. 다음 이메일에 대한 정밀 스팸 분석을 수행해주세요.

=== 이메일 정보 ===
제목: {email_subject}
내용: {email_content}

=== 1차 AI 분석 결과 ===
판별: {'스팸' if koelectra_result.get('is_spam') else '정상'}
신뢰도: {koelectra_result.get('confidence', 0):.3f}
정상 확률: {koelectra_result.get('probabilities', {}).get('정상', 0):.3f}
스팸 확률: {koelectra_result.get('probabilities', {}).get('스팸', 0):.3f}

=== 분석 요청사항 ===
다음 관점에서 종합적으로 분석해주세요:

1. **발신자 신뢰성 분석**
   - 이메일 주소의 합법성
   - 도메인의 신뢰성
   - 발신자 정보의 일관성

2. **내용 진정성 분석**
   - 문체와 어조의 자연스러움
   - 맞춤법과 문법의 정확성
   - 내용의 논리적 일관성

3. **피싱/사기 위험성**
   - 개인정보 요구 여부
   - 금전 관련 요구사항
   - 긴급성을 강조하는 표현
   - 의심스러운 링크나 첨부파일

4. **광고성 여부**
   - 상업적 목적의 내용
   - 과도한 홍보 문구
   - 할인/이벤트 관련 내용

5. **기술적 지표**
   - 이메일 헤더 정보 (가능한 경우)
   - HTML/텍스트 구조
   - 숨겨진 텍스트나 이미지

=== 결론 ===
최종 판단과 그 근거를 명확히 제시하고, 다음 중 하나로 분류해주세요:
- **정상**: 안전한 이메일로 판단
- **스팸**: 스팸으로 분류 권장
- **보류**: 추가 검토 필요

분석 결과를 구체적이고 명확하게 설명해주세요.
"""

        try:
            analysis = await self.generate_response(prompt)
            logger.info("EXAONE 상세 분석 완료")
            return analysis

        except Exception as e:
            logger.error(f"EXAONE 상세 분석 실패: {e}")
            return f"분석 중 오류 발생: {str(e)}"

    async def get_quick_verdict(
        self,
        email_text: str,
        koelectra_confidence: float
    ) -> str:
        """빠른 판정 (간단한 경우)"""

        prompt = f"""
다음 이메일에 대한 빠른 스팸 판정을 해주세요.

이메일 내용: {email_text}
1차 AI 신뢰도: {koelectra_confidence:.3f}

간단히 다음 중 하나로 답변해주세요:
- 정상: 안전한 이메일
- 스팸: 스팸 메일
- 불확실: 추가 분석 필요

판정 근거를 2-3줄로 간단히 설명해주세요.
"""

        try:
            verdict = await self.generate_response(prompt)
            logger.info("EXAONE 빠른 판정 완료")
            return verdict

        except Exception as e:
            logger.error(f"EXAONE 빠른 판정 실패: {e}")
            return f"판정 중 오류 발생: {str(e)}"

    def get_service_info(self) -> Dict[str, Any]:
        """서비스 정보 반환"""
        return {
            "model_path": self.model_path,
            "adapter_path": self.adapter_path,
            "max_new_tokens": self.max_new_tokens,
            "temperature": self.temperature,
            "service_type": "EXAONE Spam Analysis",
            "is_initialized": self.chat_service is not None
        }


# 전역 인스턴스 (싱글톤 패턴)
_exaone_instance = None

def get_exaone_service(
    model_path: str = "app/model/exaone-2.4b",
    adapter_path: Optional[str] = None
) -> ExaoneService:
    """EXAONE 서비스 싱글톤 인스턴스 가져오기"""
    global _exaone_instance

    if _exaone_instance is None:
        _exaone_instance = ExaoneService(
            model_path=model_path,
            adapter_path=adapter_path
        )
        logger.info("새로운 EXAONE 서비스 인스턴스 생성")

    return _exaone_instance


if __name__ == "__main__":
    # 테스트 코드
    import asyncio

    async def test_exaone():
        try:
            # 서비스 생성
            service = ExaoneService()

            # 테스트 이메일
            test_subject = "긴급! 계정 확인 필요"
            test_content = "안녕하세요. 보안상 문제로 계정 확인이 필요합니다. 아래 링크를 클릭하여 즉시 확인해주세요."

            # KoELECTRA 가상 결과
            koelectra_result = {
                "is_spam": True,
                "confidence": 0.85,
                "probabilities": {"정상": 0.15, "스팸": 0.85}
            }

            # 상세 분석 테스트
            print("=== EXAONE 상세 분석 테스트 ===")
            analysis = await service.analyze_spam_detailed(
                test_subject, test_content, koelectra_result
            )
            print(f"분석 결과:\n{analysis}")

            # 빠른 판정 테스트
            print("\n=== EXAONE 빠른 판정 테스트 ===")
            verdict = await service.get_quick_verdict(
                f"{test_subject} {test_content}", 0.85
            )
            print(f"판정 결과:\n{verdict}")

        except Exception as e:
            print(f"테스트 실패: {e}")
            import traceback
            traceback.print_exc()

    # 비동기 테스트 실행
    asyncio.run(test_exaone())
