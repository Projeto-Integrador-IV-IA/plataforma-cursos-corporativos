"""Chamada bem-sucedida alimenta o consumo diario agregado (RNF22, card #22).

O que este teste protege: ``StructuringService.structure`` soma os tokens de
toda chamada que responde com sucesso ao acumulado do dia - o insumo que
``GET /api/v1/consumption`` expoe e que ``LLM_DAILY_TOKEN_BUDGET`` vigia.
Chamada que falha nao soma tokens que o provedor nunca informou.
"""

from collections.abc import Callable

import pytest

from app.core.consumption import ConsumoDeLLM, consultar_consumo
from app.core.exceptions import LLMUnavailableError
from app.providers import CompletionParams, CompletionResult, LLMProvider, MockLLMProvider
from app.services.structuring_service import RawDemand, StructuringService
from tests.conftest import MakeSettings

DEMANDA = RawDemand(demand_id="dem-2026-0099", text="Texto de teste qualquer.")

MontarServico = Callable[..., StructuringService]


class _ProviderQueSempreFalha(LLMProvider):
    name = "programado"

    async def complete(
        self,
        prompt: str,
        params: CompletionParams | None = None,
    ) -> CompletionResult:
        raise LLMUnavailableError(provider="programado", model="modelo-remoto-1")


async def _nao_dormir(segundos: float) -> None:
    """Espera de mentira: a politica de retentativa nao atrasa o teste."""


@pytest.fixture(autouse=True)
def _consumo_isolado(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mesma isolacao de ``test_consumption.py``: singleton novo por teste."""

    monkeypatch.setattr("app.core.consumption._consumo", ConsumoDeLLM())


@pytest.fixture
def montar_servico(make_settings: MakeSettings) -> MontarServico:
    def _montar(provider: LLMProvider, **overrides: object) -> StructuringService:
        base: dict[str, object] = {"llm_max_retries": 0}
        base.update(overrides)
        return StructuringService(provider, make_settings(**base), sleep=_nao_dormir)

    return _montar


async def test_chamada_bem_sucedida_soma_ao_consumo_do_dia(
    montar_servico: MontarServico,
) -> None:
    servico = montar_servico(MockLLMProvider())

    outcome = await servico.structure(DEMANDA)

    consumo = consultar_consumo()
    assert consumo.chamadas == 1
    assert consumo.tokens_entrada == outcome.completion.usage.prompt_tokens
    assert consumo.tokens_saida == outcome.completion.usage.completion_tokens


async def test_duas_chamadas_bem_sucedidas_acumulam(montar_servico: MontarServico) -> None:
    servico = montar_servico(MockLLMProvider())

    await servico.structure(DEMANDA)
    await servico.structure(DEMANDA)

    assert consultar_consumo().chamadas == 2


async def test_chamada_que_falha_nao_soma_tokens(montar_servico: MontarServico) -> None:
    servico = montar_servico(_ProviderQueSempreFalha())

    outcome = await servico.structure(DEMANDA)

    assert not outcome.succeeded
    assert consultar_consumo().chamadas == 0


async def test_limite_diario_do_ambiente_e_o_que_dispara_alerta(
    montar_servico: MontarServico,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """``llm_daily_token_budget`` da configuracao chega intacto ao alerta."""

    servico = montar_servico(MockLLMProvider(), llm_daily_token_budget=1)

    with caplog.at_level("WARNING"):
        await servico.structure(DEMANDA)

    alertas = [r for r in caplog.records if "Limite diario" in r.message]
    assert len(alertas) == 1
