"""LLM 구성 및 주입 지점을 정의하는 패키지.

이 패키지는 FastAPI 백엔드에서 사용할 LLM 객체를
구체적인 구현(예: OpenAI, Hugging Face, 로컬 모델 등)과
분리하기 위한 **추상 계층**입니다.

- LLM 타입 정의: `app.core.llm.base.LLMType`
- 기본 OpenAI provider 예시: `app.core.llm.providers.openai.create_openai_chat_llm`

사용자는 이 패키지 내부에 새로운 provider 모듈을 추가하고,
`create_custom_llm()` 같은 팩토리 함수를 만들어 원하는 LLM을
`app.core.rag_chain.create_rag_chain(vectorstore, llm=...)` 에
주입하면 됩니다.
"""

from .base import LLMType  # 재사용을 위한 타입 별칭
from .factory import create_llm_from_config

__all__ = ["LLMType", "create_llm_from_config"]
