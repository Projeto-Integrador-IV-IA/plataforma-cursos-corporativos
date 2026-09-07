"""Testes do provedor HTTP, sem rede: transporte dublado por ``httpx.MockTransport``."""

import json
from collections.abc import Callable

import httpx
import pytest

from app.core.exceptions import (
    LLMInvalidResponseError,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMUnavailableError,
)
from app.providers import CompletionParams, HttpLLMProvider
from tests.conftest import MakeSettings

RESPOSTA_OK = {
    "model": "modelo-remoto-1",
    "choices": [{"message": {"content": '{"tema": "lideranca"}'}, "finish_reason": "stop"}],
    "usage": {"prompt_tokens": 310, "completion_tokens": 128},
}


@pytest.fixture
def settings_http(make_settings: MakeSettings) -> Callable[..., object]:
    def _make(**overrides: object) -> object:
        base: dict[str, object] = {
            "llm_provider": "http",
            "llm_model": "modelo-remoto-1",
            "llm_api_key": "chave-de-teste-do-ambiente",
            "llm_base_url": "https://api.exemplo.invalid/v1",
            "llm_max_retries": 0,
        }
        base.update(overrides)
        return make_settings(**base)

    return _make


def _provider(
    settings: object, handler: Callable[[httpx.Request], httpx.Response]
) -> HttpLLMProvider:
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return HttpLLMProvider(settings, client=client)  # type: ignore[arg-type]


def _responder(
    payload: dict[str, object], status: int = 200, headers: dict[str, str] | None = None
):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json=payload, headers=headers)

    return handler


async def test_caminho_feliz_devolve_texto_e_metadados(
    settings_http: Callable[..., object],
) -> None:
    provider = _provider(settings_http(), _responder(RESPOSTA_OK))

    result = await provider.complete("prompt de extracao")

    assert result.text == '{"tema": "lideranca"}'
    assert result.provider == "http"
    assert result.model == "modelo-remoto-1"
    assert result.usage.total_tokens == 438
    assert result.finish_reason == "stop"
    assert result.latency_ms >= 0


async def test_requisicao_usa_endpoint_modelo_e_chave_do_ambiente(
    settings_http: Callable[..., object],
) -> None:
    capturadas: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        capturadas.append(request)
        return httpx.Response(200, json=RESPOSTA_OK)

    provider = _provider(settings_http(), handler)
    await provider.complete(
        "prompt de extracao", CompletionParams(system_prompt="voce e um analista")
    )

    (requisicao,) = capturadas
    corpo = json.loads(requisicao.content)
    assert str(requisicao.url) == "https://api.exemplo.invalid/v1/chat/completions"
    assert requisicao.headers["authorization"] == "Bearer chave-de-teste-do-ambiente"
    assert corpo["model"] == "modelo-remoto-1"
    assert corpo["temperature"] == 0.2
    assert corpo["messages"] == [
        {"role": "system", "content": "voce e um analista"},
        {"role": "user", "content": "prompt de extracao"},
    ]


async def test_caminho_do_endpoint_vem_da_configuracao(
    settings_http: Callable[..., object],
) -> None:
    capturadas: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        capturadas.append(request)
        return httpx.Response(200, json=RESPOSTA_OK)

    provider = _provider(settings_http(llm_completions_path="v2/responses"), handler)
    await provider.complete("prompt")

    assert str(capturadas[0].url) == "https://api.exemplo.invalid/v1/v2/responses"


async def test_schema_de_saida_e_repassado_ao_fornecedor(
    settings_http: Callable[..., object],
) -> None:
    capturadas: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        capturadas.append(request)
        return httpx.Response(200, json=RESPOSTA_OK)

    schema = {"type": "object", "properties": {"tema": {"type": "string"}}}
    provider = _provider(settings_http(), handler)
    await provider.complete("prompt", CompletionParams(response_schema=schema))

    corpo = json.loads(capturadas[0].content)
    assert corpo["response_format"]["type"] == "json_schema"
    assert corpo["response_format"]["json_schema"]["schema"] == schema


async def test_timeout_do_transporte_vira_excecao_tipada(
    settings_http: Callable[..., object],
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("estourou", request=request)

    provider = _provider(settings_http(), handler)

    with pytest.raises(LLMTimeoutError) as excinfo:
        await provider.complete("prompt")

    assert excinfo.value.timeout_seconds == 30.0
    assert excinfo.value.details["provider"] == "http"


async def test_erro_de_conexao_vira_indisponibilidade(
    settings_http: Callable[..., object],
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("recusou", request=request)

    provider = _provider(settings_http(), handler)

    with pytest.raises(LLMUnavailableError):
        await provider.complete("prompt")


@pytest.mark.parametrize(
    ("status", "erro"),
    [
        (408, LLMTimeoutError),
        (429, LLMRateLimitError),
        (500, LLMUnavailableError),
        (503, LLMUnavailableError),
        (504, LLMTimeoutError),
        (401, LLMInvalidResponseError),
        (422, LLMInvalidResponseError),
    ],
)
async def test_status_http_e_traduzido_para_a_excecao_correspondente(
    settings_http: Callable[..., object],
    status: int,
    erro: type[Exception],
) -> None:
    provider = _provider(settings_http(), _responder({"error": "falhou"}, status=status))

    with pytest.raises(erro) as excinfo:
        await provider.complete("prompt")

    assert excinfo.value.details["status_code"] == status  # type: ignore[attr-defined]


async def test_limite_de_uso_aproveita_o_cabecalho_retry_after(
    settings_http: Callable[..., object],
) -> None:
    provider = _provider(
        settings_http(),
        _responder({}, status=429, headers={"retry-after": "12"}),
    )

    with pytest.raises(LLMRateLimitError) as excinfo:
        await provider.complete("prompt")

    assert excinfo.value.retry_after_seconds == 12.0


@pytest.mark.parametrize(
    "corpo",
    [
        {"choices": []},
        {"choices": [{"message": {}}]},
        {"choices": [{"message": {"content": "   "}}]},
        {"sem_choices": True},
    ],
)
async def test_corpo_incompleto_ou_vazio_e_resposta_invalida(
    settings_http: Callable[..., object],
    corpo: dict[str, object],
) -> None:
    provider = _provider(settings_http(), _responder(corpo))

    with pytest.raises(LLMInvalidResponseError):
        await provider.complete("prompt")


async def test_corpo_que_nao_e_json_e_resposta_invalida(
    settings_http: Callable[..., object],
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="<html>portal de erro</html>")

    provider = _provider(settings_http(), handler)

    with pytest.raises(LLMInvalidResponseError):
        await provider.complete("prompt")


async def test_falha_retentavel_e_repetida_ate_o_limite_configurado(
    settings_http: Callable[..., object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tentativas: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        tentativas.append(1)
        if len(tentativas) < 3:
            return httpx.Response(503, json={})
        return httpx.Response(200, json=RESPOSTA_OK)

    monkeypatch.setattr("app.providers.http_llm_provider.asyncio.sleep", _sem_espera)
    provider = _provider(settings_http(llm_max_retries=2), handler)

    result = await provider.complete("prompt")

    assert len(tentativas) == 3
    assert result.text == '{"tema": "lideranca"}'


async def test_falha_nao_retentavel_nao_e_repetida(
    settings_http: Callable[..., object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tentativas: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        tentativas.append(1)
        return httpx.Response(401, json={})

    monkeypatch.setattr("app.providers.http_llm_provider.asyncio.sleep", _sem_espera)
    provider = _provider(settings_http(llm_max_retries=3), handler)

    with pytest.raises(LLMInvalidResponseError):
        await provider.complete("prompt")

    assert len(tentativas) == 1


async def test_retentativa_esgotada_propaga_a_ultima_falha(
    settings_http: Callable[..., object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tentativas: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        tentativas.append(1)
        return httpx.Response(503, json={})

    monkeypatch.setattr("app.providers.http_llm_provider.asyncio.sleep", _sem_espera)
    provider = _provider(settings_http(llm_max_retries=1), handler)

    with pytest.raises(LLMUnavailableError):
        await provider.complete("prompt")

    assert len(tentativas) == 2


def test_provedor_http_exige_endpoint(make_settings: MakeSettings) -> None:
    settings = make_settings(llm_provider="mock", llm_base_url=None)

    with pytest.raises(ValueError, match="LLM_BASE_URL"):
        HttpLLMProvider(settings)


async def test_chave_nunca_aparece_na_mensagem_de_erro(
    settings_http: Callable[..., object],
) -> None:
    provider = _provider(settings_http(), _responder({"error": "falhou"}, status=401))

    with pytest.raises(LLMInvalidResponseError) as excinfo:
        await provider.complete("prompt")

    assert "chave-de-teste-do-ambiente" not in str(excinfo.value)
    assert "chave-de-teste-do-ambiente" not in json.dumps(excinfo.value.to_error_payload())


async def _sem_espera(segundos: float) -> None:
    """Substitui o backoff nos testes, para que a suite nao durma."""
