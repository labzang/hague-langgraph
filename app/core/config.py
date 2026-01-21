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


def test_config_loading() -> dict:
    """설정 로딩 테스트 및 정보 출력."""
    print("\n" + "="*60)
    print("[테스트] 설정 로딩 테스트")
    print("="*60)

    config_info = {
        "database_url_env_set": settings.database_url_env is not None,
        "database_url": None,
        "postgres_config": {
            "host": settings.postgres_host,
            "port": settings.postgres_port,
            "db": settings.postgres_db,
            "user": settings.postgres_user,
        }
    }

    if settings.database_url_env:
        print(f"[설정] ✅ DATABASE_URL 환경변수가 설정되어 있습니다.")
        parsed = urlparse(settings.database_url_env)
        masked_url = f"{parsed.scheme}://{parsed.hostname}:{parsed.port}{parsed.path}"
        print(f"[설정] DATABASE_URL (마스킹됨): {masked_url}")
        config_info["database_url"] = masked_url
    else:
        print(f"[설정] ⚠️ DATABASE_URL 환경변수가 설정되지 않았습니다.")
        print(f"[설정] POSTGRES_* 환경변수를 사용합니다:")
        print(f"  - HOST: {settings.postgres_host}")
        print(f"  - PORT: {settings.postgres_port}")
        print(f"  - DB: {settings.postgres_db}")
        print(f"  - USER: {settings.postgres_user}")

    # 최종 database_url 확인
    final_url = settings.database_url
    parsed_final = urlparse(final_url)
    masked_final = f"{parsed_final.scheme}://{parsed_final.hostname}:{parsed_final.port}{parsed_final.path}"
    print(f"[설정] 최종 연결 문자열 (마스킹됨): {masked_final}")
    print("="*60 + "\n")

    return config_info


if __name__ == "__main__":
    """설정 테스트를 위한 직접 실행."""
    print("\n" + "="*60)
    print("Neon DB 설정 테스트")
    print("="*60)

    # 설정 로딩 테스트
    config_info = test_config_loading()

    # 연결 테스트
    try:
        import psycopg2
        print("[테스트] 데이터베이스 연결 시도...")
        conn = psycopg2.connect(settings.database_url)
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"[성공] ✅ 연결 성공!")
        print(f"[정보] PostgreSQL 버전: {version}")
        cursor.close()
        conn.close()
        print("="*60 + "\n")
    except Exception as e:
        print(f"[실패] ❌ 연결 실패: {e}")
        print("="*60 + "\n")
