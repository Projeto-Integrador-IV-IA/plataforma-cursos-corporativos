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
from app.models import Artifact, ArtifactVersion, Client, Demand, User
from app.repositories.demand_repository import DemandRepository


@pytest.fixture
def engine(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Engine]:
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
def company(engine: Engine) -> UUID:
    with Session(engine) as session:
        client = Client(name="Empresa de teste")
        session.add(client)
        session.commit()
        return client.id


def test_create_persists_negotiation_with_client_and_owner(
    api: TestClient, engine: Engine, company: UUID
) -> None:
    with Session(engine) as session:
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
    with Session(engine) as session:
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


def test_missing_client_is_refused_without_persisting(api: TestClient, engine: Engine) -> None:
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
    with Session(engine) as session:
        assert session.scalar(sa.select(sa.func.count(Demand.id))) == 0


def test_missing_owner_is_refused(api: TestClient, engine: Engine, company: UUID) -> None:
    response = api.post(
        "/api/v1/demands",
        json={"client_id": str(company), "title": "Demanda", "owner_id": str(uuid4())},
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "USER_NOT_FOUND"
    with Session(engine) as session:
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
    api: TestClient, engine: Engine, company: UUID, invalid_fields: dict[str, Any]
) -> None:
    response = api.post(
        "/api/v1/demands",
        json={"client_id": str(company), "title": "Demanda", **invalid_fields},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert response.json()["error"]["details"]
    assert "detail" not in response.json()
    with Session(engine) as session:
        assert session.scalar(sa.select(sa.func.count(Demand.id))) == 0


@pytest.mark.parametrize("payload", [{"title": "Sem cliente"}, {"client_id": str(uuid4())}])
def test_required_fields_cannot_be_omitted(api: TestClient, payload: dict[str, str]) -> None:
    response = api.post("/api/v1/demands", json=payload, headers={"X-Request-ID": "invalid-demand"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert response.json()["error"]["request_id"] == "invalid-demand"


def test_database_rejects_orphan_even_when_api_is_bypassed(engine: Engine) -> None:
    for client_id in (None, uuid4()):
        with Session(engine) as session, pytest.raises(IntegrityError):
            session.add(Demand(client_id=client_id, title="Orfa"))
            session.commit()


def test_client_with_demand_cannot_be_deleted(
    api: TestClient, engine: Engine, company: UUID
) -> None:
    assert (
        api.post(
            "/api/v1/demands", json={"client_id": str(company), "title": "Demanda"}
        ).status_code
        == 201
    )
    with engine.begin() as connection, pytest.raises(IntegrityError):
        connection.execute(sa.delete(Client).where(Client.id == company))


def test_removed_client_between_validation_and_insert_is_a_conflict(
    api: TestClient, engine: Engine, company: UUID, monkeypatch: pytest.MonkeyPatch
) -> None:
    original_create = DemandRepository.create

    def remove_parent_before_insert(repository: DemandRepository, demand: Demand) -> Demand:
        repository.session.execute(sa.delete(Client).where(Client.id == demand.client_id))
        return original_create(repository, demand)

    monkeypatch.setattr(DemandRepository, "create", remove_parent_before_insert)
    response = api.post("/api/v1/demands", json={"client_id": str(company), "title": "Demanda"})
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "DEMAND_REFERENCE_CONFLICT"
    with Session(engine) as session:
        assert session.scalar(sa.select(sa.func.count(Demand.id))) == 0
        assert session.get(Client, company) is not None  # rollback da transacao inteira


def test_migration_checks_title_and_preserves_existing_demand(
    engine: Engine, company: UUID
) -> None:
    with Session(engine) as session:
        demand = Demand(client_id=company, title="Historico", description="Contexto preservado")
        session.add(demand)
        session.commit()
        demand_id = demand.id

    config = Config("alembic.ini")
    command.downgrade(config, "20260902_1200")
    command.upgrade(config, "head")
    command.check(config)

    inspector = sa.inspect(engine)
    assert (
        next(c for c in inspector.get_columns("demands") if c["name"] == "client_id")["nullable"]
        is False
    )
    assert "ck_demands_title_not_blank" in {
        constraint["name"] for constraint in inspector.get_check_constraints("demands")
    }
    with Session(engine) as session:
        assert session.get(Demand, demand_id).description == "Contexto preservado"
    with Session(engine) as session, pytest.raises(IntegrityError):
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


def test_versioned_contract_matches_published_demand_operations(api: TestClient) -> None:
    import yaml

    contract_path = Path(__file__).resolve().parents[4] / (
        "packages/contracts/openapi/pipeline-service.yaml"
    )
    contract = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
    published = api.get("/openapi.json").json()
    assert contract["paths"]["/api/v1/demands"] == published["paths"]["/api/v1/demands"]
    detail_path = "/api/v1/demands/{demand_id}"
    assert contract["paths"][detail_path] == published["paths"][detail_path]
    for name, schema in published["components"]["schemas"].items():
        assert contract["components"]["schemas"][name] == schema


def test_get_returns_context_client_stage_and_linked_artifacts(
    api: TestClient, engine: Engine, company: UUID
) -> None:
    with Session(engine) as session:
        demand = Demand(client_id=company, title="Lideranca", description="Contexto original")
        session.add(demand)
        session.flush()
        artifact = Artifact(demand_id=demand.id, type="REQUISITOS_EXTRAIDOS", title="Estrutura")
        session.add(artifact)
        session.flush()
        version = ArtifactVersion(
            artifact_id=artifact.id,
            number=1,
            content={"tema": "Lideranca"},
            origin="IA",
        )
        session.add(version)
        session.commit()
        demand_id = demand.id
        artifact_id = artifact.id

    response = api.get(f"/api/v1/demands/{demand_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["description"] == "Contexto original"
    assert body["current_stage"] == "CAPTACAO"
    assert body["client"]["id"] == str(company)
    assert body["client"]["name"] == "Empresa de teste"
    assert body["artifacts"][0]["id"] == str(artifact_id)
    assert body["artifacts"][0]["versions"][0]["content"] == {"tema": "Lideranca"}


def test_patch_is_partial_and_next_get_reflects_changes(
    api: TestClient, engine: Engine, company: UUID
) -> None:
    with Session(engine) as session:
        demand = Demand(client_id=company, title="Titulo anterior", description="Contexto anterior")
        session.add(demand)
        session.commit()
        demand_id = demand.id

    patched = api.patch(
        f"/api/v1/demands/{demand_id}",
        json={"description": "Contexto revisado"},
    )

    assert patched.status_code == 200
    assert patched.json()["description"] == "Contexto revisado"
    assert patched.json()["title"] == "Titulo anterior"
    fetched = api.get(f"/api/v1/demands/{demand_id}")
    assert fetched.status_code == 200
    assert fetched.json()["description"] == "Contexto revisado"
    assert fetched.json()["client_id"] == str(company)
    assert fetched.json()["current_stage"] == "CAPTACAO"


@pytest.mark.parametrize("method", ["get", "patch"])
def test_missing_demand_returns_typed_404(api: TestClient, method: str) -> None:
    demand_id = uuid4()
    response = getattr(api, method)(
        f"/api/v1/demands/{demand_id}",
        **({"json": {"description": "Novo contexto"}} if method == "patch" else {}),
        headers={"X-Request-ID": "missing-demand"},
    )
    assert response.status_code == 404
    assert response.json()["error"] == {
        "code": "DEMAND_NOT_FOUND",
        "message": "Demanda nao encontrada.",
        "details": {"demand_id": str(demand_id)},
        "request_id": "missing-demand",
    }


@pytest.mark.parametrize(
    "payload",
    [
        {"title": None},
        {"title": "   "},
        {"current_stage": "PROPOSTA"},
        {"status": "GANHA"},
        {"client_id": str(uuid4())},
    ],
)
def test_patch_rejects_invalid_or_non_context_fields(
    api: TestClient, engine: Engine, company: UUID, payload: dict[str, Any]
) -> None:
    with Session(engine) as session:
        demand = Demand(client_id=company, title="Preservar", description="Contexto")
        session.add(demand)
        session.commit()
        demand_id = demand.id

    response = api.patch(f"/api/v1/demands/{demand_id}", json=payload)
    assert response.status_code == 422
    with Session(engine) as session:
        unchanged = session.get(Demand, demand_id)
        assert unchanged.title == "Preservar"
        assert unchanged.description == "Contexto"


def test_swagger_documents_detail_and_partial_update(api: TestClient) -> None:
    document = api.get("/openapi.json").json()
    operations = document["paths"]["/api/v1/demands/{demand_id}"]
    assert {"get", "patch"} == set(operations)
    assert {"200", "404", "422"} <= set(operations["get"]["responses"])
    assert {"200", "404", "422"} <= set(operations["patch"]["responses"])
    update_schema = document["components"]["schemas"]["DemandUpdate"]
    assert "required" not in update_schema
    assert update_schema["additionalProperties"] is False
