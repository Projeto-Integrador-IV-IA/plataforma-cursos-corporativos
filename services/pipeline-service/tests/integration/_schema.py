"""Andaime comum dos testes de integracao: schema migrado e registros base.

Os testes de integracao rodam contra o schema real, aplicado pela migration
inicial em um SQLite em memoria com ``PRAGMA foreign_keys=ON``. Constantes e
inserts vivem aqui para que cada arquivo de teste trate de um assunto so.
"""

import importlib
from collections.abc import Iterator
from typing import Any

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy.engine import Connection
from sqlalchemy.exc import IntegrityError

MIGRATION_MODULE = "app.db.migrations.versions.20260902_1200_enforce_referential_integrity"

USER_ID = "00000000000000000000000000000001"
CLIENT_ID = "00000000000000000000000000000002"
OTHER_CLIENT_ID = "00000000000000000000000000000003"
DEMAND_ID = "00000000000000000000000000000004"
OTHER_DEMAND_ID = "00000000000000000000000000000005"
RAW_INPUT_ID = "00000000000000000000000000000006"
ARTIFACT_ID = "00000000000000000000000000000007"


def migrated_connection() -> Iterator[Connection]:
    """Aplica a migration em um banco relacional com FKs habilitadas."""

    engine = sa.create_engine("sqlite+pysqlite:///:memory:")

    @sa.event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection: Any, _connection_record: Any) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    migration = importlib.import_module(MIGRATION_MODULE)

    with engine.connect() as connection:
        migration.op = Operations(MigrationContext.configure(connection))
        migration.upgrade()
        connection.commit()

        yield connection

        migration.downgrade()
        connection.commit()

    engine.dispose()


def insert_user(database: Connection) -> None:
    database.execute(
        sa.text(
            """
            INSERT INTO users (id, name, email, password_hash)
            VALUES (:id, 'Operador', 'operador@example.com', 'hash')
            """
        ),
        {"id": USER_ID},
    )
    database.commit()


def insert_client(database: Connection, client_id: str = CLIENT_ID) -> None:
    database.execute(
        sa.text("INSERT INTO clients (id, name) VALUES (:id, 'Cliente')"),
        {"id": client_id},
    )
    database.commit()


def insert_demand(
    database: Connection,
    demand_id: str = DEMAND_ID,
    client_id: str = CLIENT_ID,
) -> None:
    database.execute(
        sa.text("INSERT INTO demands (id, client_id, title) VALUES (:id, :client_id, 'Demanda')"),
        {"id": demand_id, "client_id": client_id},
    )
    database.commit()


def assert_rejected(database: Connection, statement: str, parameters: dict[str, Any]) -> None:
    """Confirma que o banco, e nao a aplicacao, recusa o registro invalido."""

    with pytest.raises(IntegrityError):
        database.execute(sa.text(statement), parameters)
    database.rollback()
