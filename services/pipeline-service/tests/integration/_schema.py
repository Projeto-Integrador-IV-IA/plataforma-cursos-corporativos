"""Andaime comum dos testes de integracao: schema migrado e registros base.

Os testes rodam contra o schema real, aplicado por **toda a cadeia Alembic** em
um SQLite em memoria com ``PRAGMA foreign_keys=ON``. Constantes e inserts vivem
aqui para que cada arquivo de teste trate de um assunto so.

A cadeia inteira, e nao a migration inicial: enquanto este andaime aplicava um
unico modulo escolhido a mao, ele divergia do banco de verdade assim que uma
migration posterior mexia no schema - foi o que aconteceu quando o RF16.1
acrescentou ``artifact_versions.raw_content``.
"""

import importlib
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy.engine import Connection
from sqlalchemy.exc import IntegrityError

VERSIONS_PACKAGE = "app.db.migrations.versions"

USER_ID = "00000000000000000000000000000001"
CLIENT_ID = "00000000000000000000000000000002"
OTHER_CLIENT_ID = "00000000000000000000000000000003"
DEMAND_ID = "00000000000000000000000000000004"
OTHER_DEMAND_ID = "00000000000000000000000000000005"
RAW_INPUT_ID = "00000000000000000000000000000006"
ARTIFACT_ID = "00000000000000000000000000000007"


def _migrations_in_order() -> list[Any]:
    """Ordena os modulos de versao seguindo os elos ``down_revision``."""

    diretorio = Path(importlib.import_module(VERSIONS_PACKAGE).__file__).parent
    modulos = [
        importlib.import_module(f"{VERSIONS_PACKAGE}.{arquivo.stem}")
        for arquivo in sorted(diretorio.glob("*.py"))
        if arquivo.stem != "__init__"
    ]
    por_revisao_anterior = {modulo.down_revision: modulo for modulo in modulos}

    cadeia: list[Any] = []
    anterior: str | None = None
    while anterior in por_revisao_anterior:
        modulo = por_revisao_anterior[anterior]
        cadeia.append(modulo)
        anterior = modulo.revision

    if len(cadeia) != len(modulos):
        nomes = {modulo.__name__ for modulo in modulos} - {m.__name__ for m in cadeia}
        raise RuntimeError(f"migration fora da cadeia de revisoes: {sorted(nomes)}")
    return cadeia


def migrated_connection() -> Iterator[Connection]:
    """Aplica a cadeia completa em um banco relacional com FKs habilitadas."""

    engine = sa.create_engine("sqlite+pysqlite:///:memory:")

    @sa.event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection: Any, _connection_record: Any) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    cadeia = _migrations_in_order()

    with engine.connect() as connection:
        operacoes = Operations(MigrationContext.configure(connection))
        for migration in cadeia:
            migration.op = operacoes
            migration.upgrade()
        connection.commit()

        yield connection

        # O desmonte roda com as FKs desligadas de proposito. O pragma existe
        # para que o teste exercite as restricoes durante o uso; mante-lo aqui
        # so faria o ``DROP TABLE`` tropecar nas linhas inseridas pelo proprio
        # teste, escondendo o que a migration reversa realmente faz.
        connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
        for migration in reversed(cadeia):
            migration.downgrade()
        connection.commit()
        connection.exec_driver_sql("PRAGMA foreign_keys=ON")

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
