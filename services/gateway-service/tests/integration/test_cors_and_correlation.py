"""CORS e correlacao de requisicao (X-Request-ID) na borda do gateway.

Sem isto, o navegador recusa a resposta do preflight (OPTIONS) a qualquer
chamada com corpo JSON - inclusive o login - porque o servidor nao declara
nenhuma origem permitida: curl e teste de integracao comum nao mostram o
problema, so um navegador real respeitando CORS.
"""

from fastapi.testclient import TestClient

from app.main import create_app


def client() -> TestClient:
    return TestClient(create_app())


def test_preflight_from_an_allowed_origin_is_accepted() -> None:
    response = client().options(
        "/api/v1/auth/login",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_preflight_from_an_unknown_origin_is_not_granted_access() -> None:
    response = client().options(
        "/api/v1/auth/login",
        headers={
            "Origin": "http://nao-e-o-frontend.invalid",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert "access-control-allow-origin" not in response.headers


def test_response_carries_a_request_id_even_when_the_client_sends_none() -> None:
    response = client().get("/health")

    assert response.headers["x-request-id"] != ""


def test_client_supplied_request_id_is_echoed_back_unchanged() -> None:
    response = client().get("/health", headers={"X-Request-ID": "id-do-cliente-123"})

    assert response.headers["x-request-id"] == "id-do-cliente-123"


def test_two_requests_without_a_client_id_get_different_generated_ids() -> None:
    first = client().get("/health").headers["x-request-id"]
    second = client().get("/health").headers["x-request-id"]

    assert first != second
