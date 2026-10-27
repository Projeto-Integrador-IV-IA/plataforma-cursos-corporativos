"""Criterios de aceite de inativacao logica e reativacao de clientes (RF01.3)."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

from app.models import Client


def client_count(engine: Engine) -> int:
    with Session(engine) as session:
        return session.scalar(select(func.count()).select_from(Client)) or 0


def test_deactivate_and_reactivate_preserve_client_history(
    api: TestClient,
    engine: Engine,
) -> None:
    created = api.post("/api/v1/clients", json={"name": "Cliente historico"})
    assert created.status_code == 201
    client_id = created.json()["id"]
    original_count = client_count(engine)

    first_deactivation = api.post(f"/api/v1/clients/{client_id}/deactivate")
    repeated_deactivation = api.post(f"/api/v1/clients/{client_id}/deactivate")

    assert first_deactivation.status_code == 200
    assert first_deactivation.json()["active"] is False
    assert repeated_deactivation.status_code == 200
    assert repeated_deactivation.json() == first_deactivation.json()

    default_listing = api.get("/api/v1/clients")
    complete_listing = api.get("/api/v1/clients?include_inactive=true")
    detail = api.get(f"/api/v1/clients/{client_id}")

    assert default_listing.status_code == 200
    assert default_listing.json()["total"] == 0
    assert default_listing.json()["items"] == []
    assert complete_listing.status_code == 200
    assert complete_listing.json()["total"] == 1
    assert complete_listing.json()["items"][0]["id"] == client_id
    assert complete_listing.json()["items"][0]["active"] is False
    assert detail.status_code == 200
    assert detail.json()["id"] == client_id
    assert detail.json()["active"] is False

    first_reactivation = api.post(f"/api/v1/clients/{client_id}/reactivate")
    repeated_reactivation = api.post(f"/api/v1/clients/{client_id}/reactivate")

    assert first_reactivation.status_code == 200
    assert first_reactivation.json()["active"] is True
    assert repeated_reactivation.status_code == 200
    assert repeated_reactivation.json() == first_reactivation.json()

    restored_listing = api.get("/api/v1/clients")
    assert restored_listing.status_code == 200
    assert restored_listing.json()["total"] == 1
    assert restored_listing.json()["items"][0]["id"] == client_id
    assert client_count(engine) == original_count


@pytest.mark.parametrize("operation", ["deactivate", "reactivate"])
def test_status_change_of_missing_client_returns_typed_404(
    api: TestClient,
    operation: str,
) -> None:
    client_id = uuid4()

    response = api.post(f"/api/v1/clients/{client_id}/{operation}")

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "CLIENT_NOT_FOUND",
            "message": "Cliente nao encontrado.",
            "details": {"client_id": str(client_id)},
        }
    }
