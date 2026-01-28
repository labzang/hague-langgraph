"""챗팅 질문 처리 오케스트레이터.

사용자 질문을 받아서 적절한 도메인 오케스트레이터로 라우팅합니다.
"""
import logging
from typing import Dict, Any

from app.domain.v10.soccer.hub.services.question_classifier import QuestionClassifier
from app.domain.v10.soccer.hub.orchestrators.player_orchestrator import PlayerOrchestrator
from app.domain.v10.soccer.hub.orchestrators.schedule_orchestrator import ScheduleOrchestrator
from app.domain.v10.soccer.hub.orchestrators.stadium_orchestrator import StadiumOrchestrator
from app.domain.v10.soccer.hub.orchestrators.team_orchestrator import TeamOrchestrator

logger = logging.getLogger(__name__)


class ChatOrchestrator:
    """챗팅 질문 처리 오케스트레이터.

    질문을 분석하여 적절한 도메인 오케스트레이터로 라우팅합니다.
    """

    def __init__(self):
        """ChatOrchestrator 초기화."""
        # 질문 분류기 초기화
        self.classifier = QuestionClassifier(use_model=False)

        # 도메인별 오케스트레이터 초기화 (지연 로딩 가능)
        self._player_orch: PlayerOrchestrator | None = None
        self._schedule_orch: ScheduleOrchestrator | None = None
        self._stadium_orch: StadiumOrchestrator | None = None
        self._team_orch: TeamOrchestrator | None = None

        logger.info("[ChatOrchestrator] 초기화 완료")

    @property
    def player_orch(self) -> PlayerOrchestrator:
        """PlayerOrchestrator 인스턴스 (지연 로딩)."""
        if self._player_orch is None:
            self._player_orch = PlayerOrchestrator()
        return self._player_orch

    @property
    def schedule_orch(self) -> ScheduleOrchestrator:
        """ScheduleOrchestrator 인스턴스 (지연 로딩)."""
        if self._schedule_orch is None:
            self._schedule_orch = ScheduleOrchestrator()
        return self._schedule_orch

    @property
    def stadium_orch(self) -> StadiumOrchestrator:
        """StadiumOrchestrator 인스턴스 (지연 로딩)."""
        if self._stadium_orch is None:
            self._stadium_orch = StadiumOrchestrator()
        return self._stadium_orch

    @property
    def team_orch(self) -> TeamOrchestrator:
        """TeamOrchestrator 인스턴스 (지연 로딩)."""
        if self._team_orch is None:
            self._team_orch = TeamOrchestrator()
        return self._team_orch

    async def process_query(self, question: str) -> Dict[str, Any]:
        """사용자 질문을 처리합니다.

        Args:
            question: 사용자 질문

        Returns:
            처리 결과 딕셔너리
        """
        logger.info(f"[ChatOrchestrator] 질문 수신: {question}")
        print(f"[ChatOrchestrator] 사용자 질문: {question}")

        # 1. 질문 분류
        classification_result = self.classifier.classify(question)
        domain = classification_result["domain"]
        confidence = classification_result["confidence"]

        logger.info(
            f"[ChatOrchestrator] 질문 분류 완료: 도메인={domain}, "
            f"신뢰도={confidence:.2f}, 방법={classification_result['method']}"
        )
        print(f"[ChatOrchestrator] 분류 결과: {domain} (신뢰도: {confidence:.2f})")

        # 2. 도메인별 오케스트레이터로 라우팅
        if domain == "player":
            logger.info("[ChatOrchestrator] PlayerOrchestrator로 라우팅")
            result = await self.player_orch.process_query(question)
        elif domain == "schedule":
            logger.info("[ChatOrchestrator] ScheduleOrchestrator로 라우팅")
            result = await self.schedule_orch.process_query(question)
        elif domain == "stadium":
            logger.info("[ChatOrchestrator] StadiumOrchestrator로 라우팅")
            result = await self.stadium_orch.process_query(question)
        elif domain == "team":
            logger.info("[ChatOrchestrator] TeamOrchestrator로 라우팅")
            result = await self.team_orch.process_query(question)
        else:
            # unknown 도메인인 경우 기본 응답
            logger.warning(f"[ChatOrchestrator] 알 수 없는 도메인: {domain}")
            result = {
                "success": False,
                "message": "질문을 이해할 수 없습니다. 축구 관련 질문을 입력해주세요.",
                "domain": domain,
                "confidence": confidence
            }

        # 3. 결과에 분류 정보 추가
        result["classification"] = classification_result
        result["routed_domain"] = domain

        logger.info(f"[ChatOrchestrator] 질문 처리 완료: 도메인={domain}")
        return result

