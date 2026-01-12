"""LLM 팩토리 함수 - 설정에 따라 적절한 LLM을 생성합니다."""

from typing import Optional

from app.config import Settings
from app.core.llm.base import LLMType
from app.core.llm.providers.openai import create_openai_chat_llm
from app.core.llm.providers.korean_hf_local import create_local_korean_llm
from app.core.llm.providers.midm_local import create_midm_local_llm


def create_llm_from_config(settings: Settings) -> Optional[LLMType]:
    """설정에 따라 적절한 LLM을 생성합니다.

    Args:
        settings: 애플리케이션 설정 객체.

    Returns:
        LLMType: 생성된 LLM 인스턴스. 설정이 불완전하면 None.

    Raises:
        ValueError: 지원하지 않는 LLM provider가 지정된 경우.
        FileNotFoundError: 로컬 모델 경로가 잘못된 경우.
    """
    provider = settings.llm_provider.lower()

    if provider == "openai":
        if not settings.openai_api_key:
            print("[경고] OpenAI API 키가 설정되지 않았습니다.")
            return None
        print("[AI] OpenAI LLM을 사용합니다.")
        return create_openai_chat_llm()

    elif provider == "korean_local":
        if not settings.local_model_dir:
            print("[경고] LOCAL_MODEL_DIR이 설정되지 않았습니다.")
            return None
        print(f"[로컬] 로컬 한국어 모델을 사용합니다: {settings.local_model_dir}")
        return create_local_korean_llm(settings.local_model_dir)

    elif provider == "midm":
        print("[AI] Midm-2.0-Mini-Instruct 모델을 사용합니다.")
        # LOCAL_MODEL_DIR이 설정되어 있으면 해당 경로 사용, 없으면 기본 경로
        model_dir = settings.local_model_dir if settings.local_model_dir else None
        return create_midm_local_llm(model_dir)

    else:
        raise ValueError(f"지원하지 않는 LLM provider: {provider}")
