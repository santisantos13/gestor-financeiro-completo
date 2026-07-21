from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

from app.core.config import settings
from app.db.base import Base

# import de todos os models para que fiquem registrados em Base.metadata
# antes do autogenerate rodar. app.models/__init__.py ja importa todas as
# entidades do dominio, entao um unico import aqui basta.
from app import models  # noqa: F401

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# URL do banco vem de uma unica fonte de verdade (app.core.config),
# evitando duplicar a string de conexao no alembic.ini.
#
# Deploy pre-alfa (2026-07-21, docs/analise-arquitetural-deploy-prealfa.md):
# `config.set_main_option` grava o valor num `configparser` por baixo dos
# panos, que trata "%" como inicio de uma interpolacao (`%(nome)s`) mesmo
# so ARMAZENANDO o valor (nao so ao ler) - qualquer DATABASE_URL com senha
# percent-encoded (ex.: "%3F" para "?") quebra com
# `ValueError: invalid interpolation syntax`. Escapar "%" como "%%" resolve:
# o configparser decodifica "%%" de volta para um "%" literal ao ler o
# valor (`get_main_option`/`get_section`, usados abaixo), entao a URL chega
# intacta na engine do SQLAlchemy.
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL.replace("%", "%%"))

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# metadata usada pelo --autogenerate
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
