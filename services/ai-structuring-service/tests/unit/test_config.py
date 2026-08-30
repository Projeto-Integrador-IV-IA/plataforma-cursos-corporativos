"""Testes da configuracao segura do provedor de LLM."""

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def _set_common_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    monkeypatch.setenv("AI_STRUCTURING_PORT", "8003")
    monkeypatch.setenv("PIPELINE_SERVICE_URL", "http://pipeline:8001")
    monkeypatch.setenv("LLM_MODEL", "test-model")
    monkeypatch.setenv("LLM_TIMEOUT_SECONDS", "30")
    monkeypatch.setenv("LLM_MAX_RETRIES", "2")
    monkeypatch.setenv("LLM_TEMPERATURE", "0.2")


def test_remote_provider_reads_and_masks_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    api_key = "chave-de-teste-fornecida-pelo-ambiente"
    _set_common_environment(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "remote")
    monkeypatch.setenv("LLM_API_KEY", api_key)

    settings = Settings()

    assert settings.llm_api_key is not None
    assert settings.llm_api_key.get_secret_value() == api_key
    assert api_key not in repr(settings)


def test_remote_provider_rejects_empty_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_common_environment(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "remote")
    monkeypatch.setenv("LLM_API_KEY", "")

    with pytest.raises(ValidationError):
        Settings()


def test_mock_provider_does_not_require_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_common_environment(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setenv("LLM_API_KEY", "")

    assert Settings().llm_api_key is None
