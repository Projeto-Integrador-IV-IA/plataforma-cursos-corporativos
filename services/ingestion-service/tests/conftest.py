"""Fixtures compartilhadas dos testes do ingestion-service.

Fixtures previstas:
    - client: cliente HTTP de teste sobre a aplicacao FastAPI;
    - settings: configuracao apontando para ambiente de teste;
    - dublês dos servicos a jusante, para que o teste de um microsservico nao
      dependa da subida dos outros.

``client`` ja esta implementada; ``settings`` e os dublês seguem pendentes.
"""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import create_app


@pytest.fixture(autouse=True)
def configured_environment(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Isola configuracao e cache entre testes, sem depender do ambiente da maquina."""

    for name, value in {
        "ENVIRONMENT": "test",
        "LOG_LEVEL": "INFO",
        "INGESTION_PORT": "8002",
        "PIPELINE_SERVICE_URL": "http://pipeline:8001",
        "AI_STRUCTURING_SERVICE_URL": "http://ai:8003",
    }.items():
        monkeypatch.setenv(name, value)
    monkeypatch.delenv("SOURCE_TEXT_MAX_LENGTH", raising=False)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def client() -> Iterator[TestClient]:
    """Cliente HTTP em processo sobre a aplicacao, sem subir servidor."""

    with TestClient(create_app()) as test_client:
        yield test_client
