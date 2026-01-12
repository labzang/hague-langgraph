"""애플리케이션 설정 관리.

이 모듈은 설정 정의만을 포함하여, 다른 모듈 간 순환 의존성을 피하기 위한
중앙 설정 모듈입니다.
"""

import os
from typing import Optional
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """애플리케이션 설정."""

    # 데이터베이스 설정 (Neon 등 외부 Postgres 포함)
    postgres_host: str = os.getenv("POSTGRES_HOST", "postgres")
    postgres_port: str = os.getenv("POSTGRES_PORT", "5432")
    postgres_db: str = os.getenv("POSTGRES_DB", "langchain_db")
    postgres_user: str = os.getenv("POSTGRES_USER", "langchain_user")
    postgres_password: str = os.getenv("POSTGRES_PASSWORD", "langchain_password")
    # .env / 환경변수의 DATABASE_URL을 읽어올 필드
    database_url_env: Optional[str] = Field(default=None, alias="DATABASE_URL")

    # OpenAI 설정
    openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY")

    # LLM 설정
    llm_provider: str = os.getenv("LLM_PROVIDER", "openai")  # openai, korean_local, midm 등
    local_model_dir: Optional[str] = os.getenv("LOCAL_MODEL_DIR")  # 로컬 모델 디렉터리 경로

    # Chat Service 설정 (QLoRA)
    chat_model_path: Optional[str] = os.getenv("CHAT_MODEL_PATH")  # QLoRA 모델 경로 또는 Hugging Face 모델 ID
    chat_adapter_path: Optional[str] = os.getenv("CHAT_ADAPTER_PATH")  # LoRA 어댑터 경로 (선택사항)
    use_chat_service: bool = os.getenv("USE_CHAT_SERVICE", "false").lower() == "true"  # Chat Service 사용 여부

    # 애플리케이션 설정
    app_name: str = "LangChain RAG API"
    app_version: str = "1.0.0"
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"

    @property
    def database_url(self) -> str:
        """데이터베이스 연결 문자열 반환.

        - `.env` 에 `DATABASE_URL` 이 설정되어 있으면 그 값을 기반으로 사용
          (예: psql에서 사용한 Neon URL). 이때 psycopg2가 이해하지 못하는
          `channel_binding` 같은 옵션은 자동으로 제거합니다.
        - 없으면 기존 POSTGRES_* 값을 조합
        """
        if self.database_url_env:
            return self._sanitize_database_url(self.database_url_env)

        return (
            f"postgresql://{self.postgres_user}:"
            f"{self.postgres_password}@"
            f"{self.postgres_host}:"
            f"{self.postgres_port}/"
            f"{self.postgres_db}"
        )

    @staticmethod
    def _sanitize_database_url(raw_url: str) -> str:
        """psycopg2용으로 DATABASE_URL을 정리.

        - `channel_binding` 등 psycopg2가 인식하지 못하는 옵션을 제거합니다.
        """
        parsed = urlparse(raw_url)
        query = dict(parse_qsl(parsed.query))

        # psycopg2에서 문제를 일으킬 수 있는 옵션 제거
        query.pop("channel_binding", None)

        sanitized = parsed._replace(query=urlencode(query))
        return urlunparse(sanitized)

    class Config:
        """Pydantic 설정."""

        env_file = ".env"
        case_sensitive = False
        # .env에 정의된 추가 키(DATABASE_URL 등)가 있어도 에러를 내지 않도록 설정
        extra = "ignore"


# 전역 설정 인스턴스
settings = Settings()
