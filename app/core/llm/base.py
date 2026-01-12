"""LLM 타입 정의 모듈.

실제 LLM 구현체(OpenAI, Hugging Face, 로컬 모델 등)는
`BaseLanguageModel` 을 구현하거나 이를 래핑한 객체여야 합니다.
이 타입을 통해 RAG 체인에 주입 가능한 LLM의 공통 인터페이스를
표현합니다.
"""

from langchain_core.language_models.base import BaseLanguageModel

# 프로젝트 전역에서 사용하는 LLM 타입 별칭
LLMType = BaseLanguageModel

__all__ = ["LLMType", "BaseLanguageModel"]
