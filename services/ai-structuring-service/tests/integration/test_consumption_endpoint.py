"""Consulta HTTP do consumo agregado de tokens (RNF22, card #22).

O que este teste protege: ``GET /api/v1/consumption`` devolve o acumulado do
dia e o teto configurado via ``LLM_DAILY_TOKEN_BUDGET``, sem exigir que tenha
havido chamada - e sem nunca repassar credencial ou texto do cliente, que esta
rota nem recebe.
"""

from collections.abc import Callable, Iterator
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.core.consumption import ConsumoDeLLM
from app.main import create_app
from tests.conftest import MakeSettings

ROTA = "/api/v1/consumption"

MontarCliente = Callable[..., TestClient]


@pytest.fixture(autouse=True)
def _consumo_isolado(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mesma isolacao dos testes unitarios: singleton novo por teste."""

    monkeypatch.setattr("app.core.consumption._consumo", ConsumoDeLLM())


@pytest.fixture
def montar_cliente(make_settings: MakeSettings) -> Iterator[MontarCliente]:
    aplicacao = create_app()

    def _montar(**overrides: object) -> TestClient:
        settings: Settings = make_settings(**overrides)
        aplicacao.dependency_overrides[get_settings] = lambda: settings
        return TestClient(aplicacao)

    yield _montar
    aplicacao.dependency_overrides.clear()


def test_sem_chamada_hoje_devolve_consumo_zerado(montar_cliente: MontarCliente) -> None:
    with montar_cliente() as client:
        resposta = client.get(ROTA)

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["calls"] == 0
    assert corpo["total_tokens"] == 0
    assert corpo["daily_limit"] is None
    assert corpo["limit_exceeded"] is False
    assert corpo["date"] == datetime.now(UTC).date().isoformat()


def test_limite_configurado_sem_consumo_nao_esta_excedido(montar_cliente: MontarCliente) -> None:
    with montar_cliente(llm_daily_token_budget=500) as client:
        resposta = client.get(ROTA)

    corpo = resposta.json()
    assert corpo["daily_limit"] == 500
    assert corpo["limit_exceeded"] is False


def test_consumo_acima_do_limite_configurado_aparece_excedido(
    montar_cliente: MontarCliente,
) -> None:
    from app.core.consumption import registrar_consumo

    registrar_consumo(tokens_entrada=400, tokens_saida=200, limite_diario=None)

    with montar_cliente(llm_daily_token_budget=500) as client:
        resposta = client.get(ROTA)

    corpo = resposta.json()
    assert corpo["calls"] == 1
    assert corpo["total_tokens"] == 600
    assert corpo["limit_exceeded"] is True


def test_data_especifica_sem_chamada_tambem_devolve_zerado(montar_cliente: MontarCliente) -> None:
    with montar_cliente() as client:
        resposta = client.get(ROTA, params={"date": "2020-01-01"})

    assert resposta.status_code == 200
    assert resposta.json()["date"] == "2020-01-01"
