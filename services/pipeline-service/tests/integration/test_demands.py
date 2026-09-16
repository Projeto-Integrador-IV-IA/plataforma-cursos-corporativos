"""Aceite RF02: HTTP real em processo sobre banco migrado com FKs habilitadas."""

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
from app.models import Client, Demand, User
from app.repositories.demand_repository import DemandRepository


@pytest.fixture
def database(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Engine]:
    """Aplica a cadeia Alembic em um banco temporario, sem acessar dados reais."""

    from app.core.config import get_settings

    database_url = f"sqlite+pysqlite:///{(tmp_path / 'demands.sqlite3').as_posix()}"
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    monkeypatch.setenv("PIPELINE_PORT", "8001")
    monkeypatch.setenv("DATABASE_URL", database_url)
    get_settings.cache_clear()
    config = Config("alembic.ini")
    command.upgrade(config, "head")
    engine = sa.create_engine(
        database_url, connect_args={"check_same_thread": False}, poolclass=StaticPool
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
def api(database: Engine) -> Iterator[TestClient]:
    application = create_app()

    def session_override() -> Iterator[Session]:
        with Session(database, expire_on_commit=False) as session:
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
def company(database: Engine) -> UUID:
    with Session(database) as session:
        client = Client(name="Empresa de teste")
        session.add(client)
        session.commit()
        return client.id


def test_create_persists_negotiation_with_client_and_owner(
    api: TestClient, database: Engine, company: UUID
) -> None:
    with Session(database) as session:
        owner = User(name="Responsavel", email="owner@example.com", password_hash="test-hash")
        session.add(owner)
        session.commit()
        owner_id = owner.id

    response = api.post(
        "/api/v1/demands",
        json={
            "client_id": str(company),
            "title": "  Treinamento de lideranca  ",
            "description": "Negociacao para capacitar vinte gestores.",
            "owner_id": str(owner_id),
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["client_id"] == str(company)
    assert body["owner_id"] == str(owner_id)
    assert body["title"] == "Treinamento de lideranca"
    assert body["status"] == "ABERTA"
    assert body["current_stage"] == "CAPTACAO"
    assert body["active"] is True
    assert body["created_at"] and body["updated_at"]
    with Session(database) as session:
        demand = session.get(Demand, UUID(body["id"]))
        assert demand is not None
        assert demand.client.id == company
        assert demand.owner.id == owner_id
        assert demand.description == body["description"]
        assert demand.title == body["title"]


def test_minimal_creation_keeps_context_and_owner_optional(api: TestClient, company: UUID) -> None:
    response = api.post("/api/v1/demands", json={"client_id": str(company), "title": "Demanda"})
    assert response.status_code == 201
    assert response.json()["description"] is None
    assert response.json()["owner_id"] is None


def test_missing_client_is_refused_without_persisting(api: TestClient, database: Engine) -> None:
    missing_id = str(uuid4())
    response = api.post(
        "/api/v1/demands",
        json={"client_id": missing_id, "title": "Demanda orfa"},
        headers={"X-Request-ID": "demand-test"},
    )
    assert response.status_code == 404
    assert response.json()["error"] == {
        "code": "CLIENT_NOT_FOUND",
        "message": "Cliente nao encontrado.",
        "details": {"client_id": missing_id},
        "request_id": "demand-test",
    }
    with Session(database) as session:
        assert session.scalar(sa.select(sa.func.count(Demand.id))) == 0


def test_missing_owner_is_refused(api: TestClient, database: Engine, company: UUID) -> None:
    response = api.post(
        "/api/v1/demands",
        json={"client_id": str(company), "title": "Demanda", "owner_id": str(uuid4())},
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "USER_NOT_FOUND"
    with Session(database) as session:
        assert session.scalar(sa.select(sa.func.count(Demand.id))) == 0


@pytest.mark.parametrize(
    "invalid_fields",
    [
        {"client_id": None},
        {"client_id": "invalid-uuid"},
        {"title": ""},
        {"title": " \t\n "},
        {"title": None},
        {"owner_id": "invalid-uuid"},
        {"status": "GANHA"},
        {"current_stage": "PROPOSTA"},
    ],
)
def test_invalid_creation_is_refused(
    api: TestClient, database: Engine, company: UUID, invalid_fields: dict[str, Any]
) -> None:
    response = api.post(
        "/api/v1/demands",
        json={"client_id": str(company), "title": "Demanda", **invalid_fields},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert response.json()["error"]["details"]
    assert "detail" not in response.json()
    with Session(database) as session:
        assert session.scalar(sa.select(sa.func.count(Demand.id))) == 0


@pytest.mark.parametrize("payload", [{"title": "Sem cliente"}, {"client_id": str(uuid4())}])
def test_required_fields_cannot_be_omitted(api: TestClient, payload: dict[str, str]) -> None:
    response = api.post("/api/v1/demands", json=payload, headers={"X-Request-ID": "invalid-demand"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert response.json()["error"]["request_id"] == "invalid-demand"


def test_database_rejects_orphan_even_when_api_is_bypassed(database: Engine) -> None:
    for client_id in (None, uuid4()):
        with Session(database) as session, pytest.raises(IntegrityError):
            session.add(Demand(client_id=client_id, title="Orfa"))
            session.commit()


def test_client_with_demand_cannot_be_deleted(
    api: TestClient, database: Engine, company: UUID
) -> None:
    assert (
        api.post(
            "/api/v1/demands", json={"client_id": str(company), "title": "Demanda"}
        ).status_code
        == 201
    )
    with database.begin() as connection, pytest.raises(IntegrityError):
        connection.execute(sa.delete(Client).where(Client.id == company))


def test_removed_client_between_validation_and_insert_is_a_conflict(
    api: TestClient, database: Engine, company: UUID, monkeypatch: pytest.MonkeyPatch
) -> None:
    original_create = DemandRepository.create

    def remove_parent_before_insert(repository: DemandRepository, demand: Demand) -> Demand:
        repository.session.execute(sa.delete(Client).where(Client.id == demand.client_id))
        return original_create(repository, demand)

    monkeypatch.setattr(DemandRepository, "create", remove_parent_before_insert)
    response = api.post("/api/v1/demands", json={"client_id": str(company), "title": "Demanda"})
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "DEMAND_REFERENCE_CONFLICT"
    with Session(database) as session:
        assert session.scalar(sa.select(sa.func.count(Demand.id))) == 0
        assert session.get(Client, company) is not None  # rollback da transacao inteira


def test_migration_checks_title_and_preserves_existing_demand(
    database: Engine, company: UUID
) -> None:
    with Session(database) as session:
        demand = Demand(client_id=company, title="Historico", description="Contexto preservado")
        session.add(demand)
        session.commit()
        demand_id = demand.id

    config = Config("alembic.ini")
    command.downgrade(config, "20260902_1200")
    command.upgrade(config, "head")
    command.check(config)

    inspector = sa.inspect(database)
    assert (
        next(c for c in inspector.get_columns("demands") if c["name"] == "client_id")["nullable"]
        is False
    )
    assert "ck_demands_title_not_blank" in {
        constraint["name"] for constraint in inspector.get_check_constraints("demands")
    }
    with Session(database) as session:
        assert session.get(Demand, demand_id).description == "Contexto preservado"
    with Session(database) as session, pytest.raises(IntegrityError):
        session.add(Demand(client_id=company, title="   "))
        session.commit()


def test_swagger_documents_creation(api: TestClient) -> None:
    assert api.get("/docs").status_code == 200
    document = api.get("/openapi.json").json()
    operation = document["paths"]["/api/v1/demands"]["post"]
    assert {"201", "404", "409", "422"} <= set(operation["responses"])
    schema = document["components"]["schemas"]["DemandCreate"]
    assert set(schema["required"]) == {"client_id", "title"}
    assert schema["additionalProperties"] is False


def test_versioned_contract_matches_published_creation(api: TestClient) -> None:
    import yaml

    contract_path = Path(__file__).resolve().parents[4] / (
        "packages/contracts/openapi/pipeline-demands-create.yaml"
    )
    contract = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
    published = api.get("/openapi.json").json()
    assert contract["paths"]["/api/v1/demands"] == published["paths"]["/api/v1/demands"]
    for name, schema in published["components"]["schemas"].items():
        assert contract["components"]["schemas"][name] == schema
