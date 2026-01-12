"""OpenAI 기반 LLM provider 예시 모듈.

이 모듈은 OpenAI Chat 모델을 사용해 `LLMType` 인스턴스를 생성하는
가장 단순한 예시입니다. 실제 서비스에서는 모델 이름, temperature 등
하이퍼파라미터를 설정에서 받아서 넘기도록 확장하면 됩니다.
"""

from typing import Any

from langchain_openai import ChatOpenAI

from app.core.llm.base import LLMType


def create_openai_chat_llm(
    model_name: str = "gpt-3.5-turbo",
    temperature: float = 0.0,
    **kwargs: Any,
) -> LLMType:
    """OpenAI Chat LLM 인스턴스를 생성합니다.

    Args:
        model_name: 사용할 OpenAI 챗 모델 이름.
        temperature: 생성 온도.
        **kwargs: `ChatOpenAI` 에 전달할 추가 인자.

    Returns:
        LLMType: LangChain 호환 LLM 인스턴스.
    """

    return ChatOpenAI(model=model_name, temperature=temperature, **kwargs)
