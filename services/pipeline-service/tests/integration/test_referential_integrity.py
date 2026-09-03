"""Provas executaveis da integridade referencial exigida pelo RNF14."""

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


@pytest.fixture
def database() -> Iterator[Connection]:
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


def test_demand_cannot_reference_missing_client(database: Connection) -> None:
    assert_rejected(
        database,
        "INSERT INTO demands (id, client_id, title) VALUES (:id, :parent_id, 'Orfa')",
        {"id": DEMAND_ID, "parent_id": CLIENT_ID},
    )


def test_raw_input_cannot_reference_missing_demand(database: Connection) -> None:
    insert_user(database)

    assert_rejected(
        database,
        """
        INSERT INTO raw_inputs (id, demand_id, original_content, source, author_id)
        VALUES (:id, :parent_id, 'Conteudo', 'EMAIL', :author_id)
        """,
        {"id": RAW_INPUT_ID, "parent_id": DEMAND_ID, "author_id": USER_ID},
    )


def test_stage_transition_cannot_reference_missing_demand(database: Connection) -> None:
    insert_user(database)

    assert_rejected(
        database,
        """
        INSERT INTO stage_transitions (id, demand_id, from_stage, to_stage, author_id)
        VALUES (:id, :parent_id, 'CAPTACAO', 'ESTRUTURACAO', :author_id)
        """,
        {"id": RAW_INPUT_ID, "parent_id": DEMAND_ID, "author_id": USER_ID},
    )


def test_artifact_cannot_reference_missing_demand(database: Connection) -> None:
    assert_rejected(
        database,
        "INSERT INTO artifacts (id, demand_id, type) VALUES (:id, :parent_id, 'EMENTA')",
        {"id": ARTIFACT_ID, "parent_id": DEMAND_ID},
    )


def test_artifact_cannot_reference_source_from_another_demand(database: Connection) -> None:
    insert_user(database)
    insert_client(database)
    insert_client(database, OTHER_CLIENT_ID)
    insert_demand(database)
    insert_demand(database, OTHER_DEMAND_ID, OTHER_CLIENT_ID)
    database.execute(
        sa.text(
            """
            INSERT INTO raw_inputs (id, demand_id, original_content, source, author_id)
            VALUES (:id, :demand_id, 'Conteudo', 'EMAIL', :author_id)
            """
        ),
        {"id": RAW_INPUT_ID, "demand_id": OTHER_DEMAND_ID, "author_id": USER_ID},
    )
    database.commit()

    assert_rejected(
        database,
        """
        INSERT INTO artifacts (id, demand_id, type, raw_input_id)
        VALUES (:id, :demand_id, 'EMENTA', :raw_input_id)
        """,
        {"id": ARTIFACT_ID, "demand_id": DEMAND_ID, "raw_input_id": RAW_INPUT_ID},
    )


def test_artifact_version_cannot_reference_missing_artifact(database: Connection) -> None:
    assert_rejected(
        database,
        """
        INSERT INTO artifact_versions (id, artifact_id, number, content, origin)
        VALUES (:id, :parent_id, 1, '{}', 'IA')
        """,
        {"id": RAW_INPUT_ID, "parent_id": ARTIFACT_ID},
    )


def test_required_relationship_cannot_be_null(database: Connection) -> None:
    required_relationships = {
        ("demands", "client_id"),
        ("raw_inputs", "demand_id"),
        ("stage_transitions", "demand_id"),
        ("artifacts", "demand_id"),
        ("artifact_versions", "artifact_id"),
    }
    inspector = sa.inspect(database)
    nullable_relationships = {
        (table, column["name"])
        for table, expected_column in required_relationships
        for column in inspector.get_columns(table)
        if column["name"] == expected_column and column["nullable"]
    }

    assert nullable_relationships == set()


def test_client_with_demand_cannot_be_deleted(database: Connection) -> None:
    insert_client(database)
    insert_demand(database)

    assert_rejected(
        database,
        "DELETE FROM clients WHERE id = :id",
        {"id": CLIENT_ID},
    )


def test_stage_accepts_only_contract_values(database: Connection) -> None:
    insert_client(database)

    assert_rejected(
        database,
        """
        INSERT INTO demands (id, client_id, title, current_stage)
        VALUES (:id, :client_id, 'Demanda', 'ETAPA_INEXISTENTE')
        """,
        {"id": DEMAND_ID, "client_id": CLIENT_ID},
    )


def test_valid_client_demand_source_and_artifact_chain_is_persisted(
    database: Connection,
) -> None:
    insert_user(database)
    insert_client(database)
    insert_demand(database)
    database.execute(
        sa.text(
            """
            INSERT INTO raw_inputs (id, demand_id, original_content, source, author_id)
            VALUES (:id, :demand_id, 'Conteudo', 'EMAIL', :author_id)
            """
        ),
        {"id": RAW_INPUT_ID, "demand_id": DEMAND_ID, "author_id": USER_ID},
    )
    database.execute(
        sa.text(
            """
            INSERT INTO artifacts (id, demand_id, type, raw_input_id)
            VALUES (:id, :demand_id, 'EMENTA', :raw_input_id)
            """
        ),
        {"id": ARTIFACT_ID, "demand_id": DEMAND_ID, "raw_input_id": RAW_INPUT_ID},
    )
    database.execute(
        sa.text(
            """
            INSERT INTO artifact_versions (id, artifact_id, number, content, origin)
            VALUES ('00000000000000000000000000000008', :artifact_id, 1, '{}', 'IA')
            """
        ),
        {"artifact_id": ARTIFACT_ID},
    )
    database.commit()

    artifact_count = database.scalar(sa.text("SELECT COUNT(*) FROM artifacts"))
    version_count = database.scalar(sa.text("SELECT COUNT(*) FROM artifact_versions"))

    assert (artifact_count, version_count) == (1, 1)
