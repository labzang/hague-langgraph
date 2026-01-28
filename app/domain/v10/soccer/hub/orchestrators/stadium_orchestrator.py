"""경기장 데이터 처리 오케스트레이터.

LangGraph StateGraph를 사용하여 정책기반/규칙기반 처리를 분기합니다.
"""
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Literal

from langgraph.graph import StateGraph, END, START

from app.core.langsmith_config import get_langsmith_config
from app.domain.v10.soccer.models.states.stadium_state import StadiumProcessingState
from app.domain.v10.soccer.spokes.agents.stadium_agent import StadiumAgent
from app.domain.v10.soccer.spokes.services.stadium_service import StadiumService

logger = logging.getLogger(__name__)


class StadiumOrchestrator:
    """경기장 데이터 처리 오케스트레이터.

    LangGraph StateGraph를 사용하여 데이터 처리 흐름을 관리합니다.
    """

    def __init__(
        self,
        model_dir: Optional[Path] = None,
    ):
        """StadiumOrchestrator 초기화.

        Args:
            model_dir: KoELECTRA 모델 디렉토리 경로 (향후 사용 예정)
        """
        self.model_dir = model_dir or self._get_default_model_dir()

        # Agent와 Service 인스턴스 생성
        self.agent = StadiumAgent()
        self.service = StadiumService()

        # LangGraph 그래프 빌드
        self.graph = self._build_graph()

        logger.info("[오케스트레이터] StadiumOrchestrator 초기화 완료 (LangGraph)")

    def _get_default_model_dir(self) -> Path:
        """기본 모델 디렉토리 경로를 반환합니다."""
        current_file = Path(__file__)
        project_root = current_file.parent.parent.parent.parent.parent.parent
        model_dir = project_root / "artifacts" / "models--monologg--koelectra-small-v3-discriminator"
        return model_dir

    def _build_graph(self) -> StateGraph:
        """LangGraph StateGraph를 빌드합니다."""
        graph = StateGraph(StadiumProcessingState)

        graph.add_node("validate", self._validate_node)
        graph.add_node("determine_strategy", self._determine_strategy_node)
        graph.add_node("policy_process", self._policy_process_node)
        graph.add_node("rule_process", self._rule_process_node)
        graph.add_node("finalize", self._finalize_node)

        graph.add_edge(START, "validate")
        graph.add_edge("validate", "determine_strategy")
        graph.add_conditional_edges(
            "determine_strategy",
            self._route_strategy,
            {
                "policy": "policy_process",
                "rule": "rule_process",
            }
        )
        graph.add_edge("policy_process", "finalize")
        graph.add_edge("rule_process", "finalize")
        graph.add_edge("finalize", END)

        return graph.compile()

    async def _validate_node(self, state: StadiumProcessingState) -> Dict[str, Any]:
        """데이터 검증 노드."""
        logger.info(f"[검증 노드] {len(state.get('items', []))}개 항목 검증 시작")

        items = state.get("items", [])
        validation_errors = []

        if not items:
            validation_errors.append({
                "error": "데이터가 비어있습니다",
                "level": "warning"
            })

        for idx, item in enumerate(items[:10]):
            if not isinstance(item, dict):
                validation_errors.append({
                    "index": idx,
                    "error": "항목이 딕셔너리 형식이 아닙니다",
                    "level": "error"
                })

        logger.info(f"[검증 노드] 검증 완료: 오류 {len(validation_errors)}개")

        return {
            "validation_errors": validation_errors
        }

    async def _determine_strategy_node(self, state: StadiumProcessingState) -> Dict[str, Any]:
        """전략 판단 노드."""
        items = state.get("items", [])
        logger.info(f"[전략 판단 노드] {len(items)}개 항목 분석 시작")

        strategy_type = "rule"

        logger.info(f"[전략 판단 노드] 선택된 전략: {strategy_type}")

        return {
            "strategy_type": strategy_type
        }

    def _route_strategy(self, state: StadiumProcessingState) -> Literal["policy", "rule"]:
        """전략 라우팅 함수."""
        strategy_type = state.get("strategy_type", "rule")
        logger.info(f"[라우팅] 전략 '{strategy_type}'로 라우팅")
        return strategy_type  # type: ignore

    async def _policy_process_node(self, state: StadiumProcessingState) -> Dict[str, Any]:
        """정책 기반 처리 노드."""
        items = state.get("items", [])
        logger.info(f"[정책 처리 노드] {len(items)}개 항목 처리 시작")

        try:
            result = await self.agent.process_stadiums(items)
            logger.info("[정책 처리 노드] 처리 완료")
            return {
                "policy_result": result
            }
        except Exception as e:
            logger.error(f"[정책 처리 노드] 처리 실패: {e}", exc_info=True)
            return {
                "policy_result": {
                    "success": False,
                    "error": str(e)
                }
            }

    async def _rule_process_node(self, state: StadiumProcessingState) -> Dict[str, Any]:
        """규칙 기반 처리 노드."""
        items = state.get("items", [])
        logger.info(f"[규칙 처리 노드] {len(items)}개 항목 처리 시작")

        try:
            result = await self.service.process_stadiums(items)
            logger.info("[규칙 처리 노드] 처리 완료")
            return {
                "rule_result": result,
                "db_result": result.get("database_result", {})
            }
        except Exception as e:
            logger.error(f"[규칙 처리 노드] 처리 실패: {e}", exc_info=True)
            return {
                "rule_result": {
                    "success": False,
                    "error": str(e)
                },
                "db_result": {}
            }

    async def _finalize_node(self, state: StadiumProcessingState) -> Dict[str, Any]:
        """최종 결과 정리 노드."""
        logger.info("[최종화 노드] 결과 정리 시작")

        strategy_type = state.get("strategy_type", "rule")

        if strategy_type == "policy":
            result = state.get("policy_result", {})
        else:
            result = state.get("rule_result", {})

        final_result = {
            **result,
            "strategy_used": strategy_type,
            "total_items": len(state.get("items", [])),
            "validation_errors_count": len(state.get("validation_errors", []))
        }

        logger.info(f"[최종화 노드] 결과 정리 완료: 전략={strategy_type}")

        return {
            "final_result": final_result
        }

    async def process_stadiums(self, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """경기장 데이터를 처리합니다.

        LangGraph StateGraph를 실행하여 데이터를 처리합니다.

        Args:
            items: 처리할 경기장 데이터 리스트

        Returns:
            처리 결과 딕셔너리
        """
        logger.info(f"[오케스트레이터] 라우터로부터 {len(items)}개 항목 수신")

        logger.info("[오케스트레이터] 수신된 데이터 상위 5개 출력:")
        top_five_items = items[:5]
        for idx, item in enumerate(top_five_items, start=1):
            logger.info(f"  [오케스트레이터 {idx}] {json.dumps(item, ensure_ascii=False, indent=2)}")

        initial_state: StadiumProcessingState = {
            "items": items,
            "validation_errors": [],
            "strategy_type": "",
            "normalized_items": [],
            "policy_result": {},
            "rule_result": {},
            "db_result": {},
            "final_result": {}
        }

        logger.info(f"[오케스트레이터] LangGraph 실행 시작: {len(items)}개 항목")

        langsmith_config = get_langsmith_config()
        if langsmith_config:
            logger.info("[오케스트레이터] LangSmith 추적 활성화")
            langsmith_config["metadata"]["domain"] = "stadium"
            langsmith_config["metadata"]["item_count"] = len(items)
            langsmith_config["tags"].append("stadium-processing")

        final_state = await self.graph.ainvoke(
            initial_state,
            config=langsmith_config
        )

        result = final_state.get("final_result", {})

        logger.info(f"[오케스트레이터] LangGraph 실행 완료: 전략={final_state.get('strategy_type', 'unknown')}")
        return result

    async def process_query(self, question: str) -> Dict[str, Any]:
        """사용자 질문을 처리합니다.

        Args:
            question: 사용자 질문

        Returns:
            처리 결과 딕셔너리
        """
        logger.info(f"[StadiumOrchestrator] 질문 수신: {question}")
        print(f"[StadiumOrchestrator] 사용자 질문: {question}")

        # 질문 처리 로직 (향후 확장 가능)
        result = {
            "success": True,
            "question": question,
            "message": "경기장 질문이 성공적으로 수신되었습니다.",
            "domain": "stadium"
        }

        logger.info(f"[StadiumOrchestrator] 질문 처리 완료: {question}")
        return result
