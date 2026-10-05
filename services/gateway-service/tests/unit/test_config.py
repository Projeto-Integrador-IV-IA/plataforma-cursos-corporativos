"""Testes da configuracao segura do gateway."""

import pytest
from pydantic import ValidationError

from app.core.config import Settings

_VARIABLES = {
    "ENVIRONMENT": "test",
    "LOG_LEVEL": "INFO",
    "GATEWAY_PORT": "8000",
    "PIPELINE_SERVICE_URL": "http://pipeline:8001",
    "INGESTION_SERVICE_URL": "http://ingestion:8002",
    "AI_STRUCTURING_SERVICE_URL": "http://ai:8003",
    "JWT_SECRET_KEY": "uma-chave-de-teste-com-mais-de-32-caracteres",
    "JWT_ALGORITHM": "HS256",
    "ACCESS_TOKEN_EXPIRE_MINUTES": "60",
}


def test_settings_read_environment_and_mask_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    for name, value in _VARIABLES.items():
        monkeypatch.setenv(name, value)

    settings = Settings()

    assert settings.gateway_port == 8000
    assert settings.jwt_secret_key.get_secret_value() == _VARIABLES["JWT_SECRET_KEY"]
    assert _VARIABLES["JWT_SECRET_KEY"] not in repr(settings)


def test_settings_reject_missing_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    for name, value in _VARIABLES.items():
        monkeypatch.setenv(name, value)
    monkeypatch.delenv("JWT_SECRET_KEY")

    with pytest.raises(ValidationError):
        Settings()
