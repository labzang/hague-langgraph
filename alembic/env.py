"""Alembic 환경 설정."""
import os
# Alembic 실행 중임을 가장 먼저 표시 (다른 import 전에 설정)
os.environ["ALEMBIC_CONTEXT"] = "1"

from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from sqlalchemy.engine import Connection

from alembic import context

# app.core.database 설정 import
from app.core.config import settings

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def get_url():
    """데이터베이스 URL 반환."""
    database_url = settings.database_url
    # Alembic은 asyncpg를 사용하지 않으므로 postgresql://로 변환
    if database_url.startswith("postgresql+asyncpg://"):
        database_url = database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    return database_url


# 모델들이 사용하는 Base를 import (모델과 동일한 Base 사용)
# 모델들이 Base.metadata에 등록되도록 import 필수
from app.domain.shared.bases import Base
from app.domain.v10.soccer.bases.players import Player
from app.domain.v10.soccer.bases.teams import Team
from app.domain.v10.soccer.bases.schedules import Schedule
from app.domain.v10.soccer.bases.stadiums import Stadium

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

