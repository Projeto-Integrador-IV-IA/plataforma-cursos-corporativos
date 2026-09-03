"""Ambiente de execucao das migrations do Alembic.

Contrato desta camada:
    - ler a URL do banco de ``DATABASE_URL`` (nunca do alembic.ini) - RNF11;
    - expor o metadata de ``app.db.base`` para autogeracao;
    - suportar modo offline (gera SQL) e online (aplica no banco).

Migrations sao parte da trilha de auditoria da modelagem: nenhuma alteracao de
schema entra sem migration versionada (RNF14 do Documento Consolidado v1.0).
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

from app.core.config import get_settings
from app.db.base import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_database_url() -> str:
    """Obtem a URL sem expor ou persistir a credencial na configuracao do Alembic."""

    return get_settings().database_url.get_secret_value()


def run_migrations_offline() -> None:
    """Gera SQL sem abrir conexao com o banco."""

    context.configure(
        url=get_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Aplica migrations em uma conexao transacional."""

    connectable = create_engine(get_database_url(), poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()

    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
