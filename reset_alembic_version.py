"""Alembic 버전 테이블 초기화 스크립트.

이 스크립트는 데이터베이스의 alembic_version 테이블을 초기화하여
마이그레이션 파일과 데이터베이스 상태를 동기화합니다.

주의: 이 스크립트는 alembic_version 테이블의 모든 데이터를 삭제합니다.
"""
from sqlalchemy import create_engine, text
from app.core.config import settings


def reset_alembic_version():
    """alembic_version 테이블 초기화."""
    # 데이터베이스 URL을 동기 방식으로 변환
    database_url = settings.database_url
    if database_url.startswith("postgresql+asyncpg://"):
        database_url = database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    elif database_url.startswith("postgresql://"):
        pass  # 이미 동기 형식
    else:
        print(f"[ERROR] 지원하지 않는 데이터베이스 URL 형식: {database_url}")
        return

    try:
        # 동기 엔진 생성
        engine = create_engine(database_url)

        with engine.connect() as conn:
            # alembic_version 테이블의 모든 데이터 삭제
            conn.execute(text("DELETE FROM alembic_version"))
            conn.commit()
            print("[SUCCESS] alembic_version 테이블이 초기화되었습니다.")
            print("이제 'alembic revision --autogenerate -m \"initial\"' 명령을 실행하세요.")
    except Exception as e:
        print(f"[ERROR] 오류 발생: {e}")
        raise


if __name__ == "__main__":
    reset_alembic_version()

