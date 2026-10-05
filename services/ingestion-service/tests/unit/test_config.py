"""Testes da configuracao do ingestion-service."""

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_settings_are_read_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    monkeypatch.setenv("INGESTION_PORT", "8002")
    monkeypatch.setenv("PIPELINE_SERVICE_URL", "http://pipeline:8001")
    monkeypatch.setenv("AI_STRUCTURING_SERVICE_URL", "http://ai:8003")

    settings = Settings()

    assert settings.ingestion_port == 8002
    assert settings.pipeline_service_url == "http://pipeline:8001"


def test_service_url_is_required(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    monkeypatch.setenv("INGESTION_PORT", "8002")
    monkeypatch.setenv("PIPELINE_SERVICE_URL", "http://pipeline:8001")
    monkeypatch.delenv("AI_STRUCTURING_SERVICE_URL", raising=False)

    with pytest.raises(ValidationError):
        Settings()
