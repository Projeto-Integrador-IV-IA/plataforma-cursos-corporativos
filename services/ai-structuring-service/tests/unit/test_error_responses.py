"""Resposta HTTP de erro do servico (RNF02, RNF05).

Falha do provedor de LLM nao pode chegar ao operador como 500 generico: o
corpo devolvido segue o contrato unico de erro da plataforma e identifica a
causa. Como as rotas de negocio ainda nao existem, o handler e exercitado
sobre uma aplicacao minima, montada aqui com o mesmo registro de
``app.main.register_exception_handlers``.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.exceptions import (
    LLMInvalidResponseError,
    LLMProviderError,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMUnavailableError,
    PlatformError,
)
from app.main import create_app, register_exception_handlers


def _app_com_falha(erro: LLMProviderError) -> FastAPI:
    """Aplicacao minima cuja unica rota levanta a falha informada."""

    application = FastAPI()
    register_exception_handlers(application)

    @application.get("/falha")
    async def falhar() -> None:
        raise erro

    return application


@pytest.mark.parametrize(
    ("erro", "status", "code"),
    [
        (LLMTimeoutError(timeout_seconds=15.0), 504, "LLM_TIMEOUT"),
        (LLMUnavailableError(), 503, "LLM_UNAVAILABLE"),
        (LLMRateLimitError(retry_after_seconds=30.0), 429, "LLM_RATE_LIMITED"),
        (LLMInvalidResponseError(), 502, "LLM_INVALID_RESPONSE"),
    ],
)
def test_falha_do_provedor_vira_resposta_de_erro_identificavel(
    erro: LLMProviderError,
    status: int,
    code: str,
) -> None:
    with TestClient(_app_com_falha(erro)) as client:
        resposta = client.get("/falha")

    assert resposta.status_code == status
    assert resposta.json()["error"]["code"] == code
    assert resposta.json()["error"]["message"] == type(erro).default_message


def test_resposta_de_erro_carrega_a_correlacao_da_requisicao() -> None:
    erro = LLMTimeoutError(timeout_seconds=15.0, provider="http", model="modelo-remoto-1")

    with TestClient(_app_com_falha(erro)) as client:
        resposta = client.get("/falha", headers={"X-Request-ID": "req-2026-0042"})

    corpo = resposta.json()["error"]
    assert corpo["request_id"] == "req-2026-0042"
    assert corpo["details"] == {
        "timeout_seconds": 15.0,
        "provider": "http",
        "model": "modelo-remoto-1",
    }


def test_resposta_de_erro_omite_a_correlacao_quando_nao_houver() -> None:
    with TestClient(_app_com_falha(LLMUnavailableError())) as client:
        resposta = client.get("/falha")

    assert "request_id" not in resposta.json()["error"]


def test_aplicacao_do_servico_registra_o_handler_de_dominio() -> None:
    assert PlatformError in create_app().exception_handlers
