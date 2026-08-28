import os

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_session
from app.main import app
from app.models.client import Client

test_engine = create_engine(
    "sqlite+pysqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSession = sessionmaker(bind=test_engine, expire_on_commit=False)
Base.metadata.create_all(test_engine)


def override_get_session():
    with TestSession() as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise


app.dependency_overrides[get_session] = override_get_session
client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_database():
    Base.metadata.drop_all(test_engine)
    Base.metadata.create_all(test_engine)
    yield


def test_create_client_persists_record() -> None:
    response = client.post(
        "/api/v1/clients",
        json={
            "nome": "Empresa Exemplo Ltda",
            "cnpj": "12.345.678/0001-90",
            "segmento": "Tecnologia",
            "contato_nome": "Maria Silva",
            "contato_email": "maria@example.com",
            "contato_telefone": "+55 11 99999-0000",
            "observacoes": "Cliente prioritario",
        },
    )

    assert response.status_code == 201
    assert response.headers["location"].startswith("/api/v1/clients/")
    assert response.json()["cnpj"] == "12345678000190"

    with Session(test_engine) as session:
        persisted = session.scalar(select(Client).where(Client.cnpj == "12345678000190"))
        assert persisted is not None
        assert persisted.nome == "Empresa Exemplo Ltda"


def test_create_client_rejects_duplicate_cnpj() -> None:
    payload = {"nome": "Outra empresa", "cnpj": "12.345.678/0001-90"}
    first_response = client.post("/api/v1/clients", json=payload)
    response = client.post("/api/v1/clients", json=payload | {"nome": "Empresa duplicada"})

    assert first_response.status_code == 201
    assert response.status_code == 409


def test_create_client_requires_non_blank_name() -> None:
    response = client.post("/api/v1/clients", json={"nome": "   "})

    assert response.status_code == 422
