import uuid

from fastapi.testclient import TestClient


def client_payload(*, name: str = "Empresa Exemplo Ltda", cnpj: str | None = None) -> dict:
    return {
        "name": name,
        "cnpj": cnpj,
        "segment": "Technology",
        "contact_name": "Maria Silva",
        "contact_email": "maria@example.com",
        "contact_phone": "+55 11 99999-0000",
        "notes": "Cliente prioritário",
    }


def test_create_then_list_and_get_client(client: TestClient) -> None:
    create_response = client.post(
        "/api/v1/clients",
        json=client_payload(cnpj="12.345.678/0001-90"),
    )

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["name"] == "Empresa Exemplo Ltda"
    assert created["cnpj"] == "12345678000190"
    assert create_response.headers["location"] == f"/api/v1/clients/{created['id']}"

    list_response = client.get("/api/v1/clients?page=1&size=20")

    assert list_response.status_code == 200
    page = list_response.json()
    assert page == {"items": [created], "total": 1, "page": 1, "size": 20}

    get_response = client.get(create_response.headers["location"])

    assert get_response.status_code == 200
    assert get_response.json() == created


def test_list_clients_is_paginated(client: TestClient) -> None:
    for index in range(3):
        response = client.post(
            "/api/v1/clients",
            json=client_payload(name=f"Client {index}"),
        )
        assert response.status_code == 201

    response = client.get("/api/v1/clients?page=2&size=2")

    assert response.status_code == 200
    assert response.json()["total"] == 3
    assert response.json()["page"] == 2
    assert response.json()["size"] == 2
    assert len(response.json()["items"]) == 1


def test_duplicate_cnpj_uses_error_contract(client: TestClient) -> None:
    payload = client_payload(cnpj="12345678000190")
    assert client.post("/api/v1/clients", json=payload).status_code == 201

    response = client.post("/api/v1/clients", json=payload | {"name": "Duplicate"})

    assert response.status_code == 409
    assert response.json() == {
        "error": {
            "code": "CLIENT_CNPJ_ALREADY_EXISTS",
            "message": "Já existe um cliente cadastrado com este CNPJ.",
        }
    }


def test_validation_error_uses_error_contract(client: TestClient) -> None:
    response = client.post(
        "/api/v1/clients",
        json=client_payload(name="   ", cnpj="1a2b3c45678901"),
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert response.json()["error"]["message"] == "Os dados informados são inválidos."
    assert response.json()["error"]["details"]["issues"]


def test_get_missing_client_uses_error_contract(client: TestClient) -> None:
    response = client.get(f"/api/v1/clients/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "CLIENT_NOT_FOUND"


def test_invalid_pagination_uses_error_contract(client: TestClient) -> None:
    response = client.get("/api/v1/clients?page=0&size=101")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_health_endpoints(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/ready").json() == {"status": "ready"}
