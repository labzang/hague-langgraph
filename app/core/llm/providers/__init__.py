"""LLM provider 구현을 위한 네임스페이스.

각 provider 모듈은 특정 백엔드(OpenAI, Hugging Face, 로컬 모델 등)에
맞는 LLM 인스턴스를 생성하는 팩토리 함수를 제공합니다.

예시:
- `openai.py`   → `create_openai_chat_llm(...)`
- `korean_hf_local.py` → `create_local_korean_llm(model_dir=...)`

이 모듈에서는 공통 인터페이스만 정의하고, 실제 선택/주입은
사용자가 애플리케이션 엔트리포인트(`app/main.py` 또는 `app/api_server.py`)에서
수행하는 것을 권장합니다.
"""

from .openai import create_openai_chat_llm
from .midm_local import create_midm_local_llm, create_midm_instruct_llm

__all__ = ["create_openai_chat_llm", "create_midm_local_llm", "create_midm_instruct_llm"]
