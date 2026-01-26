"""
데이터베이스 모듈
루즈한 결합도로 설계된 공통 Base와 믹스인 제공
"""
from app.core.database.base import Base
from app.core.database.mixin import (
    TimestampMixin,
    SoftDeleteMixin,
    StatusMixin,
)

# Alembic 환경에서는 session import를 지연시킴 (asyncpg 불필요)
# alembic이 실행 중일 때는 session을 import하지 않음
import sys
import os

# Alembic 실행 여부 확인
_is_alembic = (
    "alembic" in sys.modules or
    os.environ.get("ALEMBIC_CONTEXT") == "1" or
    any("alembic" in str(arg) for arg in sys.argv)
)

if not _is_alembic:
    from app.core.database.session import (
        engine,
        AsyncSessionLocal,
        get_db,
        init_database,
        check_migration_status,
        close_database,
        create_database_engine,
    )
else:
    # Alembic 환경에서는 None으로 설정
    engine = None
    AsyncSessionLocal = None
    get_db = None
    init_database = None
    check_migration_status = None
    close_database = None
    create_database_engine = None

__all__ = [
    # Base
    "Base",
    # Mixins
    "TimestampMixin",
    "SoftDeleteMixin",
    "StatusMixin",
    # Session
    "engine",
    "AsyncSessionLocal",
    "get_db",
    "init_database",
    "check_migration_status",
    "close_database",
    "create_database_engine",
]
