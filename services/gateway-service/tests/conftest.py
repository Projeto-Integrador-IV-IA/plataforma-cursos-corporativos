"""Fixtures compartilhadas dos testes do gateway-service.

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

from app.main import create_app


@pytest.fixture
def client() -> Iterator[TestClient]:
    """Cliente HTTP em processo sobre a aplicacao, sem subir servidor."""

    with TestClient(create_app()) as test_client:
        yield test_client
