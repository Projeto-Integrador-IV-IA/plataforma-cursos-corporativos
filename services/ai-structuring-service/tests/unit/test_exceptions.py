"""Testes das excecoes tipadas do provedor de LLM (RNF03, RNF05)."""

import pytest

from app.core.exceptions import (
    LLMInvalidResponseError,
    LLMProviderError,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMUnavailableError,
    PlatformError,
    UpstreamError,
)

CONDICOES_DE_FALHA = [
    (LLMUnavailableError, "LLM_UNAVAILABLE", 503, True),
    (LLMTimeoutError, "LLM_TIMEOUT", 504, True),
    (LLMRateLimitError, "LLM_RATE_LIMITED", 429, True),
    (LLMInvalidResponseError, "LLM_INVALID_RESPONSE", 502, False),
]


@pytest.mark.parametrize(("erro", "code", "http_status", "retryable"), CONDICOES_DE_FALHA)
def test_condicao_de_falha_tem_codigo_status_e_politica_de_retentativa(
    erro: type[LLMProviderError],
    code: str,
    http_status: int,
    retryable: bool,
) -> None:
    assert erro.code == code
    assert erro.http_status == http_status
    assert erro.retryable is retryable


@pytest.mark.parametrize("erro", [caso[0] for caso in CONDICOES_DE_FALHA])
def test_toda_falha_do_provedor_deriva_da_excecao_base_do_servico(
    erro: type[LLMProviderError],
) -> None:
    instancia = erro()

    assert isinstance(instancia, LLMProviderError)
    assert isinstance(instancia, UpstreamError)
    assert isinstance(instancia, PlatformError)
    assert isinstance(instancia, Exception)


def test_codigos_das_quatro_condicoes_sao_distintos() -> None:
    codigos = {erro.code for erro, *_ in CONDICOES_DE_FALHA}

    assert len(codigos) == len(CONDICOES_DE_FALHA)


def test_mensagem_padrao_e_usada_quando_o_chamador_nao_informa() -> None:
    erro = LLMUnavailableError()

    assert erro.message == LLMUnavailableError.default_message
    assert str(erro) == erro.message


def test_mensagem_do_chamador_prevalece() -> None:
    erro = LLMUnavailableError("Fornecedor recusou a conexao.")

    assert erro.message == "Fornecedor recusou a conexao."


def test_contexto_do_provedor_vai_para_os_detalhes() -> None:
    erro = LLMInvalidResponseError(provider="mock", model="mock-1", details={"campo": "ementa"})

    assert erro.provider == "mock"
    assert erro.model == "mock-1"
    assert erro.details == {"campo": "ementa", "provider": "mock", "model": "mock-1"}


def test_timeout_registra_o_limite_estourado() -> None:
    erro = LLMTimeoutError(timeout_seconds=15.0)

    assert erro.timeout_seconds == 15.0
    assert erro.details["timeout_seconds"] == 15.0


def test_limite_de_uso_registra_a_espera_sugerida() -> None:
    erro = LLMRateLimitError(retry_after_seconds=30.0)

    assert erro.retry_after_seconds == 30.0
    assert erro.details["retry_after_seconds"] == 30.0


def test_payload_segue_o_contrato_de_erro_da_plataforma() -> None:
    erro = LLMTimeoutError(timeout_seconds=15.0, provider="mock")

    payload = erro.to_error_payload(request_id="req-123")

    assert payload == {
        "error": {
            "code": "LLM_TIMEOUT",
            "message": LLMTimeoutError.default_message,
            "details": {"timeout_seconds": 15.0, "provider": "mock"},
            "request_id": "req-123",
        }
    }


def test_payload_omite_detalhes_e_correlacao_quando_nao_ha() -> None:
    payload = LLMUnavailableError().to_error_payload()

    assert payload == {
        "error": {
            "code": "LLM_UNAVAILABLE",
            "message": LLMUnavailableError.default_message,
        }
    }


def test_detalhes_de_uma_instancia_nao_vazam_para_outra() -> None:
    primeiro = LLMUnavailableError(details={"tentativa": 1})
    segundo = LLMUnavailableError()

    assert primeiro.details == {"tentativa": 1}
    assert segundo.details == {}
