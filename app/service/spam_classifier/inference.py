"""
KoELECTRA 스팸 분류기 추론 서비스
"""

import torch
import time
import logging
from typing import Dict, Any, List
from pathlib import Path
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from peft import PeftModel

logger = logging.getLogger(__name__)

class SpamClassifier:
    """KoELECTRA LoRA 기반 스팸 분류기"""

    def __init__(
        self,
        model_path: str,
        base_model: str = "monologg/koelectra-small-v3-discriminator",
        max_length: int = 256,
        device: str = None
    ):
        """
        Args:
            model_path: LoRA 어댑터 경로
            base_model: 베이스 모델 이름
            max_length: 최대 토큰 길이
            device: 디바이스 ('cuda', 'cpu', None=auto)
        """
        self.model_path = Path(model_path)
        self.base_model = base_model
        self.max_length = max_length
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")

        # 라벨 매핑
        self.label_names = {0: "정상", 1: "스팸"}

        # 모델과 토크나이저 로드
        self._load_model()

        logger.info(f"SpamClassifier 초기화 완료 - 디바이스: {self.device}")

    def _load_model(self):
        """모델과 토크나이저 로드"""
        try:
            # 토크나이저 로드
            self.tokenizer = AutoTokenizer.from_pretrained(self.base_model)
            logger.info(f"토크나이저 로드 완료: {self.base_model}")

            # 베이스 모델 로드
            base_model = AutoModelForSequenceClassification.from_pretrained(
                self.base_model,
                num_labels=2,
                torch_dtype=torch.float32
            )

            # LoRA 어댑터 로드
            if self.model_path.exists():
                self.model = PeftModel.from_pretrained(base_model, str(self.model_path))
                logger.info(f"LoRA 어댑터 로드 완료: {self.model_path}")
            else:
                logger.warning(f"LoRA 어댑터 경로가 존재하지 않음: {self.model_path}")
                self.model = base_model

            # 디바이스 이동 및 평가 모드
            self.model.to(self.device)
            self.model.eval()

            logger.info("모델 로드 및 설정 완료")

        except Exception as e:
            logger.error(f"모델 로드 실패: {e}")
            raise

    def preprocess(self, text: str) -> Dict[str, torch.Tensor]:
        """텍스트 전처리"""
        try:
            # 토큰화
            encoding = self.tokenizer(
                text,
                truncation=True,
                padding=True,
                max_length=self.max_length,
                return_tensors="pt"
            )

            # 디바이스 이동
            encoding = {k: v.to(self.device) for k, v in encoding.items()}

            return encoding

        except Exception as e:
            logger.error(f"전처리 실패: {e}")
            raise

    def predict(self, text: str) -> Dict[str, Any]:
        """스팸 분류 예측"""
        start_time = time.time()

        try:
            # 전처리
            inputs = self.preprocess(text)

            # 추론
            with torch.no_grad():
                outputs = self.model(**inputs)
                logits = outputs.logits

                # 확률 계산
                probabilities = torch.softmax(logits, dim=-1)
                predicted_class = torch.argmax(probabilities, dim=-1).item()
                confidence = probabilities[0][predicted_class].item()

                # 결과 구성
                result = {
                    "is_spam": bool(predicted_class == 1),
                    "predicted_class": predicted_class,
                    "predicted_label": self.label_names[predicted_class],
                    "confidence": float(confidence),
                    "probabilities": {
                        "정상": float(probabilities[0][0]),
                        "스팸": float(probabilities[0][1])
                    },
                    "processing_time": time.time() - start_time,
                    "input_length": len(text),
                    "model_path": str(self.model_path)
                }

                logger.debug(f"예측 완료: {result['predicted_label']} (신뢰도: {confidence:.3f})")
                return result

        except Exception as e:
            logger.error(f"예측 실패: {e}")
            raise

    def predict_batch(self, texts: List[str]) -> List[Dict[str, Any]]:
        """배치 예측"""
        results = []

        for text in texts:
            try:
                result = self.predict(text)
                results.append(result)
            except Exception as e:
                logger.error(f"배치 예측 중 오류 (텍스트: {text[:50]}...): {e}")
                results.append({
                    "error": str(e),
                    "text": text[:100]
                })

        return results

    def get_model_info(self) -> Dict[str, Any]:
        """모델 정보 반환"""
        return {
            "model_path": str(self.model_path),
            "base_model": self.base_model,
            "device": self.device,
            "max_length": self.max_length,
            "label_names": self.label_names,
            "model_type": type(self.model).__name__,
            "tokenizer_vocab_size": len(self.tokenizer) if self.tokenizer else None
        }


# 전역 인스턴스 (싱글톤 패턴)
_classifier_instance = None

def get_classifier(
    model_path: str = "app/model/spam/lora/run_20260115_1313",
    base_model: str = "monologg/koelectra-small-v3-discriminator"
) -> SpamClassifier:
    """스팸 분류기 싱글톤 인스턴스 가져오기"""
    global _classifier_instance

    if _classifier_instance is None:
        _classifier_instance = SpamClassifier(
            model_path=model_path,
            base_model=base_model
        )
        logger.info("새로운 SpamClassifier 인스턴스 생성")

    return _classifier_instance


if __name__ == "__main__":
    # 테스트 코드
    logging.basicConfig(level=logging.INFO)

    try:
        # 분류기 생성
        classifier = SpamClassifier(
            model_path="app/model/spam/lora/run_20260115_1313"
        )

        # 테스트 텍스트들
        test_texts = [
            "안녕하세요. 주문 확인 메일입니다.",
            "긴급! 지금 클릭하면 1억원 당첨! 바로 송금하세요!",
            "회의 일정 변경 안내드립니다.",
            "무료 대출! 신용불량자도 OK! 즉시 승인!"
        ]

        print("=== 스팸 분류 테스트 ===")
        for text in test_texts:
            result = classifier.predict(text)
            print(f"텍스트: {text}")
            print(f"결과: {result['predicted_label']} (신뢰도: {result['confidence']:.3f})")
            print(f"처리시간: {result['processing_time']:.3f}초")
            print("-" * 50)

        # 모델 정보 출력
        print("\n=== 모델 정보 ===")
        info = classifier.get_model_info()
        for key, value in info.items():
            print(f"{key}: {value}")

    except Exception as e:
        logger.error(f"테스트 실패: {e}")
        import traceback
        traceback.print_exc()
