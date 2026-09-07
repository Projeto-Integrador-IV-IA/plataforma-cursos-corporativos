"""Fixtures compartilhadas dos testes do ai-structuring-service.

Fixtures previstas:
    - client: cliente HTTP de teste sobre a aplicacao FastAPI;
    - settings: configuracao apontando para ambiente de teste;
    - dublês dos servicos a jusante, para que o teste de um microsservico nao
      dependa da subida dos outros.

TODO(scaffolding): implementar o cliente HTTP quando app/main.py existir.
"""

from collections.abc import Callable

import pytest

from app.core.config import Settings

MakeSettings = Callable[..., Settings]


@pytest.fixture
def make_settings() -> MakeSettings:
    """Devolve uma fabrica de ``Settings`` de teste, sem depender do ambiente.

    Os valores padrao descrevem o cenario de desenvolvimento: provedor mock,
    sem chave e sem endpoint. Cada teste sobrescreve so o que lhe interessa.
    """

    def _make(**overrides: object) -> Settings:
        base: dict[str, object] = {
            "environment": "test",
            "log_level": "INFO",
            "ai_structuring_port": 8003,
            "pipeline_service_url": "http://pipeline:8001",
            "llm_provider": "mock",
            "llm_model": "mock",
            "llm_api_key": None,
            "llm_base_url": None,
            "llm_timeout_seconds": 30.0,
            "llm_max_retries": 2,
            "llm_temperature": 0.2,
        }
        base.update(overrides)
        return Settings(**base)  # type: ignore[arg-type]

    return _make
