"""Testes da configuracao segura do pipeline."""

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_database_url_comes_from_environment_and_is_masked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = "database-url-fornecida-pelo-ambiente"
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    monkeypatch.setenv("PIPELINE_PORT", "8001")
    monkeypatch.setenv("DATABASE_URL", database_url)

    settings = Settings()

    assert settings.database_url.get_secret_value() == database_url
    assert database_url not in repr(settings)


def test_database_url_is_required(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    monkeypatch.setenv("PIPELINE_PORT", "8001")
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(ValidationError):
        Settings()
