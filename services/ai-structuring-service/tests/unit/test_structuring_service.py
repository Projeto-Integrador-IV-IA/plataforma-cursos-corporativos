"""Tratamento de falha e timeout do LLM no caso de uso (RNF05).

RNF05 na matriz de rastreabilidade; **RF18.1** no Documento Consolidado de
Requisitos v1.0.

O que estes testes protegem, em uma frase: o provedor pode falhar de todas as
formas previstas que a demanda bruta continua inteira na mao do chamador, e o
erro devolvido diz qual foi a causa.

O provedor e sempre um duble - roteiro programado ou transporte HTTP dublado.
Nenhum teste toca rede, chave ou custo (RNF12).
"""

import json
from collections.abc import Callable

import httpx
import pytest

from app.core.exceptions import (
    LLMInvalidResponseError,
    LLMProviderError,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMUnavailableError,
)
from app.providers import CompletionParams, CompletionResult, HttpLLMProvider, LLMProvider
from app.services.structuring_service import (
    RawDemand,
    StructuringOutcome,
    StructuringService,
)
from tests.conftest import MakeSettings

TEXTO_COLADO = """
Boa tarde! Precisamos de um treinamento de NR-12 para os 25 tecnicos da manutencao da planta 2,
em dois dias de 8 horas, no proprio site. Fico no aguardo da proposta.
"""

DEMANDA = RawDemand(demand_id="dem-2026-0042", text=TEXTO_COLADO)

RESPOSTA_DO_MODELO = '{"tema": "NR-12 para manutencao"}'

RESPOSTA_HTTP_OK = {
    "model": "modelo-remoto-1",
    "choices": [{"message": {"content": RESPOSTA_DO_MODELO}, "finish_reason": "stop"}],
    "usage": {"prompt_tokens": 310, "completion_tokens": 128},
}


class _ProviderProgramado(LLMProvider):
    """Provedor de teste que segue um roteiro: cada passo e um texto ou uma falha.

    Esgotado o roteiro, o ultimo passo se repete - e assim que se descreve
    "falha sempre" sem precisar saber quantas tentativas a politica vai gastar.
    """

    name = "programado"

    def __init__(self, *roteiro: str | LLMProviderError) -> None:
        self.roteiro = list(roteiro)
        self.chamadas: list[tuple[str, CompletionParams | None]] = []

    async def complete(
        self,
        prompt: str,
        params: CompletionParams | None = None,
    ) -> CompletionResult:
        self.chamadas.append((prompt, params))
        passo = self.roteiro[min(len(self.chamadas), len(self.roteiro)) - 1]
        if isinstance(passo, LLMProviderError):
            raise passo
        return CompletionResult(text=passo, provider=self.name, model="programado-1")


class _Relogio:
    """Registra as esperas pedidas pela politica, sem dormir de verdade."""

    def __init__(self) -> None:
        self.esperas: list[float] = []

    async def dormir(self, segundos: float) -> None:
        self.esperas.append(segundos)


@pytest.fixture
def relogio() -> _Relogio:
    return _Relogio()


@pytest.fixture
def montar_servico(
    make_settings: MakeSettings,
    relogio: _Relogio,
) -> Callable[..., StructuringService]:
    """Monta o caso de uso sobre um provedor dado, sem espera real."""

    def _montar(provider: LLMProvider, **overrides: object) -> StructuringService:
        base: dict[str, object] = {"llm_max_retries": 0}
        base.update(overrides)
        return StructuringService(provider, make_settings(**base), sleep=relogio.dormir)

    return _montar


def _provider_http(settings: object, handler: Callable[[httpx.Request], httpx.Response]):
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return HttpLLMProvider(settings, client=client)  # type: ignore[arg-type]


def _settings_http(make_settings: MakeSettings, **overrides: object) -> object:
    base: dict[str, object] = {
        "llm_provider": "http",
        "llm_model": "modelo-remoto-1",
        "llm_api_key": "chave-de-teste-do-ambiente",
        "llm_base_url": "https://api.exemplo.invalid/v1",
        "llm_max_retries": 0,
    }
    base.update(overrides)
    return make_settings(**base)


# ----------------------------------------------------------------------
# Caminho feliz
# ----------------------------------------------------------------------


async def test_caminho_feliz_devolve_a_saida_do_modelo_e_a_demanda(
    montar_servico: Callable[..., StructuringService],
) -> None:
    servico = montar_servico(_ProviderProgramado(RESPOSTA_DO_MODELO))

    outcome = await servico.structure(DEMANDA)

    assert outcome.succeeded
    assert outcome.completion is not None
    assert outcome.completion.text == RESPOSTA_DO_MODELO
    assert outcome.error is None
    assert outcome.attempts == 1
    assert outcome.demand is DEMANDA
    assert outcome.to_error_payload() is None
    assert outcome.raise_for_error().text == RESPOSTA_DO_MODELO


async def test_prompt_montado_prevalece_sobre_o_texto_cru(
    montar_servico: Callable[..., StructuringService],
) -> None:
    provider = _ProviderProgramado(RESPOSTA_DO_MODELO)
    servico = montar_servico(provider)

    await servico.structure(DEMANDA, prompt="instrucoes + " + TEXTO_COLADO)

    enviado, _ = provider.chamadas[0]
    assert enviado.startswith("instrucoes + ")
    assert TEXTO_COLADO in enviado


async def test_timeout_do_ambiente_e_aplicado_quando_o_chamador_nao_informa(
    montar_servico: Callable[..., StructuringService],
) -> None:
    provider = _ProviderProgramado(RESPOSTA_DO_MODELO)
    servico = montar_servico(provider, llm_timeout_seconds=12.0)

    await servico.structure(DEMANDA)

    _, params = provider.chamadas[0]
    assert params is not None
    assert params.timeout_seconds == 12.0


async def test_timeout_informado_pelo_chamador_nao_e_sobrescrito(
    montar_servico: Callable[..., StructuringService],
) -> None:
    provider = _ProviderProgramado(RESPOSTA_DO_MODELO)
    servico = montar_servico(provider, llm_timeout_seconds=12.0)

    await servico.structure(DEMANDA, params=CompletionParams(timeout_seconds=3.0))

    _, params = provider.chamadas[0]
    assert params is not None
    assert params.timeout_seconds == 3.0


# ----------------------------------------------------------------------
# Timeout: o caso central de RNF05
# ----------------------------------------------------------------------


async def test_timeout_do_provedor_vira_desfecho_de_falha_sem_excecao_vazada(
    montar_servico: Callable[..., StructuringService],
) -> None:
    falha = LLMTimeoutError(timeout_seconds=15.0, provider="programado")
    servico = montar_servico(_ProviderProgramado(falha))

    outcome = await servico.structure(DEMANDA)

    assert not outcome.succeeded
    assert isinstance(outcome.error, LLMTimeoutError)
    assert outcome.completion is None


async def test_apos_timeout_a_demanda_bruta_continua_recuperavel(
    montar_servico: Callable[..., StructuringService],
) -> None:
    """Criterio de aceite: o texto colado sobrevive a falha e pode ser reprocessado."""

    provider = _ProviderProgramado(LLMTimeoutError(timeout_seconds=15.0))
    servico = montar_servico(provider)

    falhou = await servico.structure(DEMANDA)

    assert falhou.demand is DEMANDA
    assert falhou.demand.text == TEXTO_COLADO
    assert falhou.demand.demand_id == "dem-2026-0042"

    # Reprocessamento da mesma demanda, sem o operador recolar nada.
    reprocessado = await montar_servico(_ProviderProgramado(RESPOSTA_DO_MODELO)).structure(
        falhou.demand
    )

    assert reprocessado.succeeded
    assert reprocessado.demand.text == TEXTO_COLADO


async def test_erro_de_timeout_identifica_a_causa_para_o_operador(
    montar_servico: Callable[..., StructuringService],
) -> None:
    """Criterio de aceite: o erro reportado diz o que aconteceu e se vale repetir."""

    falha = LLMTimeoutError(timeout_seconds=15.0, provider="programado", model="programado-1")
    servico = montar_servico(_ProviderProgramado(falha), llm_max_retries=1)

    outcome = await servico.structure(DEMANDA)
    payload = outcome.to_error_payload(request_id="req-77")

    assert payload is not None
    assert payload["error"]["code"] == "LLM_TIMEOUT"
    assert payload["error"]["message"] == LLMTimeoutError.default_message
    assert payload["error"]["request_id"] == "req-77"
    assert payload["error"]["details"] == {
        "timeout_seconds": 15.0,
        "provider": "programado",
        "model": "programado-1",
        "demand_id": "dem-2026-0042",
        "attempts": 2,
        "retryable": True,
    }
    assert outcome.retryable


async def test_timeout_do_transporte_http_chega_tipado_ao_caso_de_uso(
    make_settings: MakeSettings,
    relogio: _Relogio,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("estourou", request=request)

    settings = _settings_http(make_settings, llm_timeout_seconds=15.0)
    servico = StructuringService(
        _provider_http(settings, handler),
        settings,  # type: ignore[arg-type]
        sleep=relogio.dormir,
    )

    outcome = await servico.structure(DEMANDA)

    assert isinstance(outcome.error, LLMTimeoutError)
    assert outcome.error.details["timeout_seconds"] == 15.0
    assert outcome.error.details["demand_id"] == "dem-2026-0042"
    assert outcome.demand.text == TEXTO_COLADO


# ----------------------------------------------------------------------
# Demais condicoes de falha
# ----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("status", "erro", "code"),
    [
        (500, LLMUnavailableError, "LLM_UNAVAILABLE"),
        (503, LLMUnavailableError, "LLM_UNAVAILABLE"),
        (504, LLMTimeoutError, "LLM_TIMEOUT"),
        (429, LLMRateLimitError, "LLM_RATE_LIMITED"),
        (401, LLMInvalidResponseError, "LLM_INVALID_RESPONSE"),
    ],
)
async def test_erro_http_do_provedor_vira_falha_identificada(
    make_settings: MakeSettings,
    relogio: _Relogio,
    status: int,
    erro: type[LLMProviderError],
    code: str,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json={"error": "falhou"})

    settings = _settings_http(make_settings)
    servico = StructuringService(
        _provider_http(settings, handler),
        settings,  # type: ignore[arg-type]
        sleep=relogio.dormir,
    )

    outcome = await servico.structure(DEMANDA)
    payload = outcome.to_error_payload()

    assert isinstance(outcome.error, erro)
    assert payload is not None
    assert payload["error"]["code"] == code
    assert payload["error"]["details"]["status_code"] == status
    assert outcome.demand.text == TEXTO_COLADO


async def test_resposta_malformada_do_fornecedor_e_falha_nao_retentavel(
    make_settings: MakeSettings,
    relogio: _Relogio,
) -> None:
    """Corpo que nao e o combinado nao vira "quase certo": e falha (ADR-0006)."""

    chamadas: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        chamadas.append(1)
        return httpx.Response(200, text="<html>portal de erro</html>")

    settings = _settings_http(make_settings, llm_max_retries=3)
    servico = StructuringService(
        _provider_http(settings, handler),
        settings,  # type: ignore[arg-type]
        sleep=relogio.dormir,
    )

    outcome = await servico.structure(DEMANDA)

    assert isinstance(outcome.error, LLMInvalidResponseError)
    assert outcome.attempts == 1
    assert len(chamadas) == 1
    assert relogio.esperas == []
    assert not outcome.retryable


async def test_falha_nao_retentavel_do_provedor_nao_e_repetida(
    montar_servico: Callable[..., StructuringService],
    relogio: _Relogio,
) -> None:
    provider = _ProviderProgramado(LLMInvalidResponseError(provider="programado"))
    servico = montar_servico(provider, llm_max_retries=3)

    outcome = await servico.structure(DEMANDA)

    assert len(provider.chamadas) == 1
    assert outcome.attempts == 1
    assert relogio.esperas == []


async def test_excecao_inesperada_nao_e_confundida_com_falha_de_provedor(
    make_settings: MakeSettings,
    relogio: _Relogio,
) -> None:
    """Defeito de programacao sobe: so falha tipada vira desfecho (RNF05)."""

    class _ProviderQuebrado(LLMProvider):
        name = "quebrado"

        async def complete(
            self,
            prompt: str,
            params: CompletionParams | None = None,
        ) -> CompletionResult:
            raise RuntimeError("defeito de programacao")

    servico = StructuringService(
        _ProviderQuebrado(),
        make_settings(llm_max_retries=3),
        sleep=relogio.dormir,
    )

    with pytest.raises(RuntimeError):
        await servico.structure(DEMANDA)

    assert relogio.esperas == []


# ----------------------------------------------------------------------
# Politica de retentativa
# ----------------------------------------------------------------------


async def test_retentativa_bem_sucedida_devolve_o_resultado(
    montar_servico: Callable[..., StructuringService],
    relogio: _Relogio,
) -> None:
    provider = _ProviderProgramado(
        LLMUnavailableError(provider="programado"),
        LLMUnavailableError(provider="programado"),
        RESPOSTA_DO_MODELO,
    )
    servico = montar_servico(provider, llm_max_retries=2)

    outcome = await servico.structure(DEMANDA)

    assert outcome.succeeded
    assert outcome.attempts == 3
    assert len(provider.chamadas) == 3
    assert relogio.esperas == [0.5, 1.0]


async def test_retentativa_bem_sucedida_sobre_o_transporte_http(
    make_settings: MakeSettings,
    relogio: _Relogio,
) -> None:
    """Indisponibilidade momentanea do fornecedor nao chega ao operador."""

    respostas: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        respostas.append(1)
        if len(respostas) < 3:
            return httpx.Response(503, json={})
        return httpx.Response(200, json=RESPOSTA_HTTP_OK)

    settings = _settings_http(make_settings, llm_max_retries=2)
    servico = StructuringService(
        _provider_http(settings, handler),
        settings,  # type: ignore[arg-type]
        sleep=relogio.dormir,
    )

    outcome = await servico.structure(DEMANDA)

    assert outcome.succeeded
    assert outcome.completion is not None
    assert outcome.completion.text == RESPOSTA_DO_MODELO
    assert outcome.attempts == 3
    assert len(respostas) == 3


async def test_retentativa_esgotada_propaga_a_ultima_falha(
    montar_servico: Callable[..., StructuringService],
    relogio: _Relogio,
) -> None:
    provider = _ProviderProgramado(LLMUnavailableError(provider="programado"))
    servico = montar_servico(provider, llm_max_retries=2)

    outcome = await servico.structure(DEMANDA)

    assert isinstance(outcome.error, LLMUnavailableError)
    assert outcome.attempts == 3
    assert outcome.error.details["attempts"] == 3
    assert len(provider.chamadas) == 3
    assert len(relogio.esperas) == 2
    assert outcome.demand.text == TEXTO_COLADO


async def test_teto_de_retentativas_zero_significa_uma_unica_tentativa(
    montar_servico: Callable[..., StructuringService],
) -> None:
    provider = _ProviderProgramado(LLMUnavailableError(provider="programado"))
    servico = montar_servico(provider, llm_max_retries=0)

    outcome = await servico.structure(DEMANDA)

    assert outcome.attempts == 1
    assert len(provider.chamadas) == 1


async def test_limite_de_uso_respeita_a_espera_sugerida_pelo_fornecedor(
    montar_servico: Callable[..., StructuringService],
    relogio: _Relogio,
) -> None:
    provider = _ProviderProgramado(
        LLMRateLimitError(retry_after_seconds=7.0, provider="programado"),
        RESPOSTA_DO_MODELO,
    )
    servico = montar_servico(provider, llm_max_retries=1)

    outcome = await servico.structure(DEMANDA)

    assert outcome.succeeded
    assert relogio.esperas == [7.0]


# ----------------------------------------------------------------------
# Fronteira com o chamador
# ----------------------------------------------------------------------


async def test_desfecho_com_falha_levanta_o_erro_tipado_na_fronteira(
    montar_servico: Callable[..., StructuringService],
) -> None:
    servico = montar_servico(_ProviderProgramado(LLMTimeoutError(timeout_seconds=15.0)))

    outcome = await servico.structure(DEMANDA)

    with pytest.raises(LLMTimeoutError):
        outcome.raise_for_error()


def test_desfecho_sem_resultado_e_sem_falha_nao_passa_silenciosamente() -> None:
    outcome = StructuringOutcome(demand=DEMANDA, attempts=0)

    with pytest.raises(LLMInvalidResponseError):
        outcome.raise_for_error()


async def test_chave_do_provedor_nunca_aparece_no_desfecho_da_falha(
    make_settings: MakeSettings,
    relogio: _Relogio,
) -> None:
    """RNF11: a credencial nao vaza em excecao, corpo de erro nem representacao."""

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("estourou", request=request)

    settings = _settings_http(make_settings, llm_max_retries=1)
    servico = StructuringService(
        _provider_http(settings, handler),
        settings,  # type: ignore[arg-type]
        sleep=relogio.dormir,
    )

    outcome = await servico.structure(DEMANDA)
    payload = json.dumps(outcome.to_error_payload(), ensure_ascii=False)

    assert "chave-de-teste-do-ambiente" not in payload
    assert "chave-de-teste-do-ambiente" not in str(outcome.error)
    assert "chave-de-teste-do-ambiente" not in repr(outcome)
    assert "authorization" not in payload.casefold()
