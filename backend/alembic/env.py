"""Ambiente do Alembic."""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import config as app_config
from app.models import Base  # importa todos os modelos

configuracao = context.config
if configuracao.config_file_name is not None:
    fileConfig(configuracao.config_file_name)

configuracao.set_main_option("sqlalchemy.url", app_config().database_url)
target_metadata = Base.metadata


def offline() -> None:
    context.configure(
        url=app_config().database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def online() -> None:
    conexao = engine_from_config(
        configuracao.get_section(configuracao.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with conexao.connect() as ligacao:
        context.configure(
            connection=ligacao,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    offline()
else:
    online()
