"""선수 데이터 처리 오케스트레이터.

GoF 전략 패턴을 사용하여 정책기반/규칙기반 처리를 분기합니다.
"""
import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Any, Optional

try:
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    logging.warning("transformers가 설치되지 않았습니다.")

from app.domain.v10.soccer.spokes.agents.player_agent import PlayerAgent
from app.domain.v10.soccer.spokes.services.player_service import PlayerService

logger = logging.getLogger(__name__)


class PlayerProcessingStrategy(ABC):
    """선수 데이터 처리 전략 인터페이스."""

    @abstractmethod
    async def process(self, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """선수 데이터를 처리합니다.

        Args:
            items: 처리할 선수 데이터 리스트

        Returns:
            처리 결과 딕셔너리
        """
        pass


class PolicyBasedStrategy(PlayerProcessingStrategy):
    """정책 기반 처리 전략.

    PlayerAgent를 사용하여 정책 기반 처리를 수행합니다.
    """

    def __init__(self):
        """PolicyBasedStrategy 초기화."""
        self.agent = PlayerAgent()
        logger.info("[전략] 정책 기반 전략 초기화 완료")

    async def process(self, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """정책 기반으로 선수 데이터를 처리합니다.

        Args:
            items: 처리할 선수 데이터 리스트

        Returns:
            처리 결과 딕셔너리
        """
        logger.info(f"[정책 기반] {len(items)}개 항목 처리 시작")
        result = await self.agent.process_players(items)
        logger.info("[정책 기반] 처리 완료")
        return result


class RuleBasedStrategy(PlayerProcessingStrategy):
    """규칙 기반 처리 전략.

    PlayerService를 사용하여 규칙 기반 처리를 수행합니다.
    """

    def __init__(self):
        """RuleBasedStrategy 초기화."""
        self.service = PlayerService()
        logger.info("[전략] 규칙 기반 전략 초기화 완료")

    async def process(self, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """규칙 기반으로 선수 데이터를 처리합니다.

        Args:
            items: 처리할 선수 데이터 리스트

        Returns:
            처리 결과 딕셔너리
        """
        logger.info(f"[규칙 기반] {len(items)}개 항목 처리 시작")
        result = await self.service.process_players(items)
        logger.info("[규칙 기반] 처리 완료")
        return result


class PlayerOrchestrator:
    """선수 데이터 처리 오케스트레이터.

    KoELECTRA 모델을 사용하여 정책기반/규칙기반을 판단하고
    적절한 전략을 선택하여 처리합니다.
    """

    def __init__(
        self,
        model_dir: Optional[Path] = None,
    ):
        """PlayerOrchestrator 초기화.

        Args:
            model_dir: KoELECTRA 모델 디렉토리 경로
        """
        self.model = None
        self.tokenizer = None
        self.model_dir = model_dir or self._get_default_model_dir()

        # 전략 인스턴스 생성
        self.policy_strategy = PolicyBasedStrategy()
        self.rule_strategy = RuleBasedStrategy()

        if TRANSFORMERS_AVAILABLE:
            self._load_model()
        else:
            logger.warning("[오케스트레이터] transformers 미설치, 기본 규칙 기반 사용")

    def _get_default_model_dir(self) -> Path:
        """기본 모델 디렉토리 경로를 반환합니다.

        Returns:
            모델 디렉토리 Path
        """
        # 프로젝트 루트 기준으로 artifacts 폴더 찾기
        current_file = Path(__file__)
        # app/domain/v10/soccer/hub/orchestrators/player_orchestrator.py
        # -> artifacts/models--monologg--koelectra-small-v3-discriminator
        project_root = current_file.parent.parent.parent.parent.parent.parent
        model_dir = project_root / "artifacts" / "models--monologg--koelectra-small-v3-discriminator"
        return model_dir

    def _load_model(self):
        """KoELECTRA 모델과 토크나이저를 로드합니다."""
        if not self.model_dir.exists():
            logger.warning(
                f"[오케스트레이터] 모델 디렉토리를 찾을 수 없습니다: {self.model_dir}. "
                "기본 규칙 기반 사용"
            )
            return

        try:
            logger.info(f"[오케스트레이터] 모델 로딩 시작: {self.model_dir}")

            # snapshots 폴더에서 최신 스냅샷 찾기
            snapshots_dir = self.model_dir / "snapshots"
            if snapshots_dir.exists():
                snapshots = list(snapshots_dir.iterdir())
                if snapshots:
                    # 가장 최근 스냅샷 사용 (일반적으로 해시 이름)
                    latest_snapshot = max(snapshots, key=lambda p: p.stat().st_mtime)
                    model_path = latest_snapshot
                    logger.info(f"[오케스트레이터] 스냅샷 사용: {model_path}")
                else:
                    model_path = self.model_dir
            else:
                model_path = self.model_dir

            # 토크나이저 로드
            self.tokenizer = AutoTokenizer.from_pretrained(
                str(model_path),
                local_files_only=True,
            )

            # 모델 로드 (SequenceClassification용)
            # discriminator 모델이므로 분류 작업에 사용
            try:
                self.model = AutoModelForSequenceClassification.from_pretrained(
                    str(model_path),
                    local_files_only=True,
                )
            except Exception:
                # SequenceClassification이 없으면 일반 모델 사용
                from transformers import AutoModel
                self.model = AutoModel.from_pretrained(
                    str(model_path),
                    local_files_only=True,
                )

            # 평가 모드로 설정
            self.model.eval()

            logger.info("[오케스트레이터] 모델 로딩 완료")

        except Exception as e:
            logger.error(f"[오케스트레이터] 모델 로딩 실패: {e}", exc_info=True)
            self.model = None
            self.tokenizer = None

    def _determine_strategy_type(self, items: List[Dict[str, Any]]) -> str:
        """선수 데이터를 분석하여 정책기반/규칙기반을 판단합니다.

        Args:
            items: 선수 데이터 리스트

        Returns:
            "policy" 또는 "rule"
        """
        if not self.model or not self.tokenizer:
            # 모델이 없으면 기본적으로 규칙 기반 사용
            logger.info("[판단] 모델 없음, 규칙 기반 선택")
            return "rule"

        try:
            # 데이터를 텍스트로 변환하여 모델에 입력
            # 간단한 휴리스틱: 데이터의 복잡도와 null 값 비율을 기반으로 판단
            total_fields = 0
            null_fields = 0
            complex_fields = 0

            for item in items[:10]:  # 최대 10개 샘플만 확인
                for key, value in item.items():
                    total_fields += 1
                    if value is None:
                        null_fields += 1
                    elif isinstance(value, (dict, list)):
                        complex_fields += 1

            null_ratio = null_fields / total_fields if total_fields > 0 else 0
            complexity_ratio = complex_fields / total_fields if total_fields > 0 else 0

            # 데이터를 텍스트로 변환
            sample_text = json.dumps(items[0] if items else {}, ensure_ascii=False)
            sample_text = sample_text[:512]  # 최대 길이 제한

            # 모델로 분류
            inputs = self.tokenizer(
                sample_text,
                return_tensors="pt",
                truncation=True,
                max_length=512,
                padding=True,
            )

            with torch.no_grad():
                outputs = self.model(**inputs)
                logits = outputs.logits if hasattr(outputs, "logits") else outputs.last_hidden_state

            # 간단한 휴리스틱: null 비율이 낮고 복잡도가 높으면 정책 기반
            # 실제로는 fine-tuned 모델이 필요하지만, 여기서는 휴리스틱 사용
            if null_ratio < 0.2 and complexity_ratio > 0.1:
                logger.info("[판단] 정책 기반 선택 (복잡한 데이터)")
                return "policy"
            else:
                logger.info("[판단] 규칙 기반 선택 (단순한 데이터)")
                return "rule"

        except Exception as e:
            logger.error(f"[판단] 오류 발생, 규칙 기반 사용: {e}", exc_info=True)
            return "rule"

    async def process_players(self, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """선수 데이터를 처리합니다.

        정책기반/규칙기반을 판단하여 적절한 전략을 선택합니다.

        Args:
            items: 처리할 선수 데이터 리스트

        Returns:
            처리 결과 딕셔너리
        """
        logger.info(f"[오케스트레이터] {len(items)}개 항목 처리 시작")

        # 전략 타입 판단
        strategy_type = self._determine_strategy_type(items)
        logger.info(f"[오케스트레이터] 선택된 전략: {strategy_type}")

        # 전략 선택 및 실행
        if strategy_type == "policy":
            strategy = self.policy_strategy
        else:
            strategy = self.rule_strategy

        result = await strategy.process(items)

        # 결과에 전략 정보 추가
        result["strategy_used"] = strategy_type
        result["total_items"] = len(items)

        logger.info(f"[오케스트레이터] 처리 완료: {strategy_type} 전략 사용")
        return result
