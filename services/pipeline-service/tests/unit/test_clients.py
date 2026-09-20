"""Criterios de aceite HTTP e persistencia de RF01.2."""

from collections.abc import Iterator
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_session
from app.main import create_app
from app.models import Client


@pytest.fixture
def client_engine() -> Iterator[Engine]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def clients_api(client_engine: Engine) -> Iterator[TestClient]:
    session_factory = sessionmaker(
        bind=client_engine,
        class_=Session,
        autoflush=False,
        expire_on_commit=False,
    )

    def override_get_session() -> Iterator[Session]:
        with session_factory() as session:
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise

    application = create_app()
    application.dependency_overrides[get_session] = override_get_session
    with TestClient(application) as test_client:
        yield test_client


def seed_client(client_engine: Engine, *, name: str = "Empresa Exemplo") -> UUID:
    with Session(client_engine) as session:
        client = Client(
            name=name,
            cnpj="12345678000190",
            segment="Tecnologia",
            contact_name="Maria Silva",
            contact_email="maria@example.com",
            contact_phone="+55 11 99999-0000",
            notes="Cliente prioritario",
        )
        session.add(client)
        session.commit()
        return client.id


def test_list_and_get_client(clients_api: TestClient, client_engine: Engine) -> None:
    client_id = seed_client(client_engine)

    page_response = clients_api.get("/api/v1/clients?page=1&size=20")
    detail_response = clients_api.get(f"/api/v1/clients/{client_id}")

    assert page_response.status_code == 200
    assert page_response.json()["total"] == 1
    assert page_response.json()["items"][0]["id"] == str(client_id)
    assert detail_response.status_code == 200
    assert detail_response.json()["name"] == "Empresa Exemplo"


def test_patch_changes_only_sent_fields_and_next_get_reflects_it(
    clients_api: TestClient, client_engine: Engine
) -> None:
    client_id = seed_client(client_engine)

    response = clients_api.patch(
        f"/api/v1/clients/{client_id}",
        json={"contact_name": "Ana Souza", "notes": None},
    )

    assert response.status_code == 200
    assert response.json()["contact_name"] == "Ana Souza"
    assert response.json()["notes"] is None
    assert response.json()["name"] == "Empresa Exemplo"
    assert response.json()["segment"] == "Tecnologia"

    following_query = clients_api.get(f"/api/v1/clients/{client_id}")
    assert following_query.status_code == 200
    assert following_query.json() == response.json()


@pytest.mark.parametrize("method", ["get", "patch"])
def test_missing_client_returns_typed_404(clients_api: TestClient, method: str) -> None:
    client_id = uuid4()
    request = getattr(clients_api, method)
    response = request(
        f"/api/v1/clients/{client_id}",
        **({"json": {"name": "Outro nome"}} if method == "patch" else {}),
    )

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "CLIENT_NOT_FOUND",
            "message": "Cliente nao encontrado.",
            "details": {"client_id": str(client_id)},
        }
    }


def test_patch_does_not_expose_rf013_active_change(
    clients_api: TestClient, client_engine: Engine
) -> None:
    client_id = seed_client(client_engine)

    response = clients_api.patch(f"/api/v1/clients/{client_id}", json={"active": False})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_swagger_documents_client_queries_and_patch(clients_api: TestClient) -> None:
    document = clients_api.get("/openapi.json").json()

    assert "get" in document["paths"]["/api/v1/clients"]
    detail = document["paths"]["/api/v1/clients/{client_id}"]
    assert {"get", "patch"} <= set(detail)
    assert "404" in detail["get"]["responses"]
    assert "404" in detail["patch"]["responses"]
    assert (
        detail["patch"]["requestBody"]["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/ClientUpdate"
    )
