"""Aceite RF16.1: resultado e fontes persistidos como um unico agregado."""

import sqlite3
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.session import get_session
from app.main import create_app
from app.models import Artifact, ArtifactSource, ArtifactVersion, Client, Demand, RawInput, User
from app.repositories.artifact_repository import ArtifactRepository


@pytest.fixture
def engine(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Engine]:
    from app.core.config import get_settings

    database_url = f"sqlite+pysqlite:///{(tmp_path / 'artifacts.sqlite3').as_posix()}"
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    monkeypatch.setenv("PIPELINE_PORT", "8001")
    monkeypatch.setenv("DATABASE_URL", database_url)
    get_settings.cache_clear()
    config = Config("alembic.ini")
    command.upgrade(config, "head")
    engine = sa.create_engine(
        database_url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @sa.event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection: Any, _connection_record: Any) -> None:
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    try:
        yield engine
    finally:
        engine.dispose()
        command.downgrade(config, "base")
        get_settings.cache_clear()


@pytest.fixture
def api(engine: Engine) -> Iterator[TestClient]:
    application = create_app()

    def session_override() -> Iterator[Session]:
        with Session(engine, expire_on_commit=False) as session:
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise

    application.dependency_overrides[get_session] = session_override
    with TestClient(application) as client:
        yield client


@pytest.fixture
def demand_with_sources(engine: Engine) -> tuple[UUID, list[UUID]]:
    with Session(engine) as session:
        client = Client(name="Empresa")
        author = User(name="Operador", email="operator@example.com", password_hash="hash")
        session.add_all([client, author])
        session.flush()
        demand = Demand(client_id=client.id, title="Curso de dados")
        session.add(demand)
        session.flush()
        sources = [
            RawInput(
                demand_id=demand.id,
                original_content="E-mail original",
                source="EMAIL",
                author_id=author.id,
            ),
            RawInput(
                demand_id=demand.id,
                original_content="Mensagem original",
                source="MENSAGENS",
                author_id=author.id,
            ),
        ]
        session.add_all(sources)
        session.commit()
        return demand.id, [source.id for source in sources]


def artifact_payload(source_ids: list[UUID]) -> dict[str, Any]:
    return {
        "type": "REQUISITOS_EXTRAIDOS",
        "title": "Estruturacao inicial",
        "raw_output": '{"tema":"Dados","carga_horaria":8}',
        "structured_content": {"tema": "Dados", "carga_horaria": 8},
        "raw_input_ids": [str(source_id) for source_id in source_ids],
        "ai_metadata": {"model": "test-model", "prompt": "extract-requirements.v2"},
    }


def test_persists_and_recovers_raw_structured_result_and_all_sources(
    api: TestClient,
    engine: Engine,
    demand_with_sources: tuple[UUID, list[UUID]],
) -> None:
    demand_id, source_ids = demand_with_sources

    created = api.post(
        f"/api/v1/demands/{demand_id}/artifacts",
        json=artifact_payload(source_ids),
    )

    assert created.status_code == 201
    body = created.json()
    assert {source["id"] for source in body["sources"]} == {str(value) for value in source_ids}
    assert body["versions"][0]["raw_output"] == '{"tema":"Dados","carga_horaria":8}'
    assert body["versions"][0]["structured_content"] == {
        "tema": "Dados",
        "carga_horaria": 8,
    }

    fetched = api.get(f"/api/v1/demands/{demand_id}/artifacts")
    assert fetched.status_code == 200
    assert fetched.json() == [body]

    with Session(engine) as session:
        assert session.scalar(sa.select(sa.func.count(Artifact.id))) == 1
        assert session.scalar(sa.select(sa.func.count(ArtifactVersion.id))) == 1
        assert session.scalar(sa.select(sa.func.count(ArtifactSource.artifact_id))) == 2


def test_rejects_source_from_another_demand_without_partial_write(
    api: TestClient,
    engine: Engine,
    demand_with_sources: tuple[UUID, list[UUID]],
) -> None:
    demand_id, _ = demand_with_sources
    with Session(engine) as session:
        client = session.scalar(sa.select(Client))
        author = session.scalar(sa.select(User))
        other = Demand(client_id=client.id, title="Outra demanda")
        session.add(other)
        session.flush()
        foreign_source = RawInput(
            demand_id=other.id,
            original_content="Fonte de outra demanda",
            source="EMAIL",
            author_id=author.id,
        )
        session.add(foreign_source)
        session.commit()
        foreign_source_id = foreign_source.id

    response = api.post(
        f"/api/v1/demands/{demand_id}/artifacts",
        json=artifact_payload([foreign_source_id]),
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ARTIFACT_SOURCE_DEMAND_MISMATCH"
    with Session(engine) as session:
        assert session.scalar(sa.select(sa.func.count(Artifact.id))) == 0
        assert session.scalar(sa.select(sa.func.count(ArtifactVersion.id))) == 0
        assert session.scalar(sa.select(sa.func.count(ArtifactSource.artifact_id))) == 0


def test_rolls_back_artifact_version_and_links_when_transaction_fails(
    api: TestClient,
    engine: Engine,
    demand_with_sources: tuple[UUID, list[UUID]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    demand_id, source_ids = demand_with_sources

    class ForcedConstraintError(Exception):
        sqlite_errorcode = sqlite3.SQLITE_CONSTRAINT_FOREIGNKEY

    def fail_after_flush(
        repository: ArtifactRepository,
        artifact: Artifact,
        version: ArtifactVersion,
        source_links: list[ArtifactSource],
    ) -> Artifact:
        artifact.versions.append(version)
        artifact.source_links.extend(source_links)
        repository.session.add(artifact)
        repository.session.flush()
        raise IntegrityError("forced failure", {}, ForcedConstraintError())

    monkeypatch.setattr(ArtifactRepository, "create_result", fail_after_flush)
    response = api.post(
        f"/api/v1/demands/{demand_id}/artifacts",
        json=artifact_payload(source_ids),
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ARTIFACT_PERSISTENCE_CONFLICT"
    with Session(engine) as session:
        assert session.scalar(sa.select(sa.func.count(Artifact.id))) == 0
        assert session.scalar(sa.select(sa.func.count(ArtifactVersion.id))) == 0
        assert session.scalar(sa.select(sa.func.count(ArtifactSource.artifact_id))) == 0


def test_swagger_documents_artifact_creation_and_consultation(api: TestClient) -> None:
    document = api.get("/openapi.json").json()
    operations = document["paths"]["/api/v1/demands/{demand_id}/artifacts"]
    assert {"get", "post"} == set(operations)
    assert {"201", "404", "409", "422"} <= set(operations["post"]["responses"])
    assert {"200", "404", "422"} <= set(operations["get"]["responses"])
