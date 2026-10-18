"""Fronteira interna para o gateway consultar credenciais (RF26, ADR-0004)."""

from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.models import User

SERVICE_KEY = "chave-interna-de-teste-com-32-caracteres"


def create_user(engine: Engine, *, email: str = "operadora@example.com") -> User:
    with Session(engine, expire_on_commit=False) as session:
        user = User(
            name="Operadora",
            email=email,
            password_hash="$2b$12$hash-nao-e-senha-em-texto-puro",
            role="OPERADOR",
        )
        session.add(user)
        session.commit()
        return user


def test_gateway_can_query_credentials_with_service_key(api: TestClient, engine: Engine) -> None:
    user = create_user(engine, email="Operadora@Example.com")
    response = api.get(
        "/api/v1/internal/auth/users/by-email",
        params={"email": "operadora@example.com"},
        headers={"X-Service-Key": SERVICE_KEY},
    )

    assert response.status_code == 200, response.text
    assert response.json() == {
        "id": str(user.id),
        "name": user.name,
        "email": "Operadora@example.com",
        "password_hash": user.password_hash,
        "role": user.role,
        "active": True,
    }


def test_internal_credentials_reject_missing_or_wrong_service_key(
    api: TestClient, engine: Engine
) -> None:
    create_user(engine)
    path = "/api/v1/internal/auth/users/by-email?email=operadora@example.com"

    assert api.get(path).status_code == 401
    assert api.get(path, headers={"X-Service-Key": "x" * 32}).status_code == 401


def test_internal_credentials_return_404_without_leaking_other_records(
    api: TestClient, engine: Engine
) -> None:
    create_user(engine)
    response = api.get(
        "/api/v1/internal/auth/users/by-email",
        params={"email": f"{uuid4()}@example.com"},
        headers={"X-Service-Key": SERVICE_KEY},
    )
    assert response.status_code == 404
