"""Aceite RF26: login, sessao protegida e expiracao configuravel."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

from app.api.v1.routes.auth import get_auth_service
from app.auth.jwt import (
    AuthenticatedUser,
    InvalidAccessTokenError,
    create_access_token,
    decode_access_token,
)
from app.auth.password import hash_password
from app.core.config import Settings, get_settings
from app.main import create_app
from app.services.auth_service import AuthService

SECRET = "segredo-de-teste-com-pelo-menos-32-caracteres"
SERVICE_KEY = "chave-interna-de-teste-com-32-caracteres"
PASSWORD = "senha-segura-de-teste"


def settings(*, expiration: int = 60, secret: str = SECRET) -> Settings:
    return Settings(
        environment="test",
        log_level="INFO",
        gateway_port=8000,
        pipeline_service_url="http://pipeline-service:8001",
        ingestion_service_url="http://ingestion-service:8002",
        ai_structuring_service_url="http://ai-structuring-service:8003",
        jwt_secret_key=secret,
        jwt_algorithm="HS256",
        access_token_expire_minutes=expiration,
        auth_service_key=SERVICE_KEY,
    )


def authenticated_api(
    handler: httpx.MockTransport,
    *,
    config: Settings | None = None,
) -> TestClient:
    active_settings = config or settings()
    app = create_app()
    client = httpx.Client(transport=handler, base_url=active_settings.pipeline_service_url)
    app.dependency_overrides[get_settings] = lambda: active_settings
    app.dependency_overrides[get_auth_service] = lambda: AuthService(client, active_settings)
    return TestClient(app)


def user_response(*, active: bool = True) -> dict[str, object]:
    return {
        "id": str(uuid4()),
        "name": "Operadora",
        "email": "operadora@example.com",
        "password_hash": hash_password(PASSWORD),
        "role": "OPERADOR",
        "active": active,
    }


def test_login_issues_token_and_protected_route_accepts_it() -> None:
    user = user_response()

    def pipeline(request: httpx.Request) -> httpx.Response:
        assert request.url.params["email"] == "operadora@example.com"
        assert request.headers["X-Service-Key"] == SERVICE_KEY
        return httpx.Response(200, json=user)

    with authenticated_api(httpx.MockTransport(pipeline)) as api:
        login = api.post(
            "/api/v1/auth/login",
            json={"email": "OPERADORA@example.com", "password": PASSWORD},
        )
        assert login.status_code == 200, login.text
        body = login.json()
        assert body["expires_in"] == 3600
        assert body["operator"] == {
            "id": user["id"],
            "name": "Operadora",
            "email": "operadora@example.com",
            "role": "OPERADOR",
        }
        verified = api.get(
            "/api/v1/auth/verify",
            headers={"Authorization": f"Bearer {body['access_token']}"},
        )

    assert verified.status_code == 200, verified.text
    assert verified.json() == {"active": True, "operator": body["operator"]}


@pytest.mark.parametrize("authorization", [None, "Basic abc", "Bearer invalido"])
def test_protected_operation_rejects_missing_or_invalid_session(
    authorization: str | None,
) -> None:
    headers = {"Authorization": authorization} if authorization else {}
    with authenticated_api(httpx.MockTransport(lambda _: httpx.Response(500))) as api:
        response = api.get("/api/v1/auth/verify", headers=headers)

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.parametrize("email_exists", [True, False])
def test_login_failure_uses_the_same_response_for_email_and_password(
    email_exists: bool,
) -> None:
    user = user_response()
    response = httpx.Response(200, json=user) if email_exists else httpx.Response(404)
    with authenticated_api(httpx.MockTransport(lambda _: response)) as api:
        login = api.post(
            "/api/v1/auth/login",
            json={"email": "operadora@example.com", "password": "senha-incorreta"},
        )

    assert login.status_code == 401
    assert login.json()["error"] == {
        "code": "INVALID_CREDENTIALS",
        "message": "E-mail ou senha incorretos.",
    }


def test_inactive_user_cannot_start_session() -> None:
    user = user_response(active=False)
    with authenticated_api(httpx.MockTransport(lambda _: httpx.Response(200, json=user))) as api:
        response = api.post(
            "/api/v1/auth/login",
            json={"email": "operadora@example.com", "password": PASSWORD},
        )
    assert response.status_code == 401


def test_session_expiration_comes_from_configuration() -> None:
    config = settings(expiration=7)
    issued_at = datetime.now(UTC)
    user = AuthenticatedUser(
        id=uuid4(), name="Operadora", email="operadora@example.com", role="OPERADOR"
    )
    token, expires_in = create_access_token(user, config, now=issued_at)

    assert expires_in == 420
    assert decode_access_token(token, config) == user

    expired, _ = create_access_token(user, config, now=issued_at - timedelta(minutes=8))
    with pytest.raises(InvalidAccessTokenError):
        decode_access_token(expired, config)


def test_token_signed_with_another_secret_is_rejected() -> None:
    user = AuthenticatedUser(
        id=uuid4(), name="Operadora", email="operadora@example.com", role="OPERADOR"
    )
    token, _ = create_access_token(user, settings())
    other = settings(secret="outro-segredo-com-pelo-menos-32-caracteres")
    with pytest.raises(InvalidAccessTokenError):
        decode_access_token(token, other)
