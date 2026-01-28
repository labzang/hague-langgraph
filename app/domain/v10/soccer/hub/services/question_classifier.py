"""질문을 도메인으로 분류하는 서비스.

사용자 질문을 분석하여 player, schedule, stadium, team 중 어느 도메인인지 판단합니다.
"""
import logging
from typing import Dict, Any, Literal, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# 도메인 타입 정의
DomainType = Literal["player", "schedule", "stadium", "team", "unknown"]


class QuestionClassifier:
    """질문을 도메인으로 분류하는 클래스.

    현재는 키워드 기반 휴리스틱을 사용하며, 향후 KoElectra 모델로 확장 가능합니다.
    """

    def __init__(
        self,
        use_model: bool = False,
        model_path: Optional[Path] = None,
    ):
        """QuestionClassifier 초기화.

        Args:
            use_model: KoElectra 모델 사용 여부 (현재는 False, 향후 확장)
            model_path: KoElectra 모델 경로
        """
        self.use_model = use_model
        self.model_path = model_path

        # 키워드 기반 분류를 위한 키워드 사전
        self.domain_keywords = {
            "player": [
                "선수", "플레이어", "손흥민", "등번호", "포지션", "국적",
                "골", "어시스트", "득점", "출전", "선발", "교체",
                "player", "선수명", "이름", "나이", "키", "몸무게"
            ],
            "schedule": [
                "경기", "일정", "스케줄", "매치", "vs", "대결",
                "경기장", "날짜", "시간", "시작", "종료",
                "schedule", "fixture", "경기 결과", "승부", "무승부"
            ],
            "stadium": [
                "경기장", "스타디움", "구장", "홈구장", "원정",
                "수용인원", "주소", "위치", "stadium", "venue"
            ],
            "team": [
                "팀", "클럽", "리그", "소속", "우승", "순위",
                "감독", "코치", "team", "club", "리그 순위",
                "승점", "승률", "승", "무", "패"
            ]
        }

        logger.info("[질문 분류기] QuestionClassifier 초기화 완료 (키워드 기반)")

    def classify(self, question: str) -> Dict[str, Any]:
        """질문을 도메인으로 분류합니다.

        Args:
            question: 사용자 질문

        Returns:
            분류 결과 딕셔너리:
            {
                "domain": "player" | "schedule" | "stadium" | "team" | "unknown",
                "confidence": float (0.0 ~ 1.0),
                "method": "keyword" | "model",
                "scores": {domain: score}  # 각 도메인별 점수
            }
        """
        question_lower = question.lower()

        if self.use_model and self.model_path:
            return self._classify_with_model(question)
        else:
            return self._classify_with_keywords(question_lower)

    def _classify_with_keywords(self, question: str) -> Dict[str, Any]:
        """키워드 기반 분류 (현재 구현).

        Args:
            question: 소문자로 변환된 질문

        Returns:
            분류 결과
        """
        scores = {}
        total_matches = 0

        # 각 도메인별 키워드 매칭 점수 계산
        for domain, keywords in self.domain_keywords.items():
            score = 0
            for keyword in keywords:
                if keyword.lower() in question:
                    score += 1
                    total_matches += 1
            scores[domain] = score

        # 점수가 가장 높은 도메인 선택
        if total_matches == 0:
            domain = "unknown"
            confidence = 0.0
        else:
            domain = max(scores, key=scores.get)  # type: ignore
            max_score = scores[domain]
            # 신뢰도 = 최고 점수 / 전체 매칭 수 (정규화)
            confidence = min(max_score / max(total_matches, 1), 1.0)

        logger.info(
            f"[질문 분류] 질문: {question[:50]}... → 도메인: {domain} "
            f"(신뢰도: {confidence:.2f}, 점수: {scores})"
        )

        return {
            "domain": domain,
            "confidence": confidence,
            "method": "keyword",
            "scores": scores
        }

    def _classify_with_model(self, question: str) -> Dict[str, Any]:
        """KoElectra 모델 기반 분류 (향후 구현).

        Args:
            question: 사용자 질문

        Returns:
            분류 결과
        """
        # TODO: KoElectra 모델 로드 및 추론
        # 예시:
        # model = AutoModelForSequenceClassification.from_pretrained(...)
        # tokenizer = AutoTokenizer.from_pretrained(...)
        # inputs = tokenizer(question, return_tensors="pt")
        # outputs = model(**inputs)
        # predicted_class = torch.argmax(outputs.logits, dim=1).item()
        # confidence = torch.softmax(outputs.logits, dim=1)[0][predicted_class].item()

        logger.warning("[질문 분류] 모델 기반 분류는 아직 구현되지 않았습니다. 키워드 기반으로 대체합니다.")
        return self._classify_with_keywords(question.lower())

    def classify_simple(self, question: str) -> DomainType:
        """간단한 분류 (도메인만 반환).

        Args:
            question: 사용자 질문

        Returns:
            도메인 타입
        """
        result = self.classify(question)
        return result["domain"]  # type: ignore

