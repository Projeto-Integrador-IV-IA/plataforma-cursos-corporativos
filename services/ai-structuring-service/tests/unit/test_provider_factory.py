"""Testes da selecao do provedor por ``LLM_PROVIDER`` (RNF03)."""

import json

import pytest

from app.core.config import get_settings
from app.providers import HttpLLMProvider, LLMProvider, MockLLMProvider, get_llm_provider
from tests.conftest import MakeSettings


def test_mock_e_o_padrao_quando_o_ambiente_nao_define_provedor(
    make_settings: MakeSettings,
) -> None:
    settings = make_settings()

    assert settings.llm_provider == "mock"
    assert settings.is_mock_provider is True
    assert isinstance(get_llm_provider(settings), MockLLMProvider)


def test_ambiente_seleciona_o_provedor_http(make_settings: MakeSettings) -> None:
    settings = make_settings(
        llm_provider="http",
        llm_api_key="chave-de-teste",
        llm_base_url="https://api.exemplo.invalid/v1",
    )

    assert isinstance(get_llm_provider(settings), HttpLLMProvider)


def test_trocar_a_variavel_troca_o_provedor_sem_mudar_o_codigo_de_chamada(
    make_settings: MakeSettings,
) -> None:
    def usar(settings: object) -> str:
        provider: LLMProvider = get_llm_provider(settings)  # type: ignore[arg-type]
        return provider.name

    assert usar(make_settings(llm_provider="mock")) == "mock"
    assert (
        usar(
            make_settings(
                llm_provider="http",
                llm_api_key="chave-de-teste",
                llm_base_url="https://api.exemplo.invalid/v1",
            )
        )
        == "http"
    )


def test_nome_do_provedor_nao_diferencia_maiusculas(make_settings: MakeSettings) -> None:
    assert isinstance(get_llm_provider(make_settings(llm_provider="MOCK")), MockLLMProvider)


def test_provedor_desconhecido_falha_na_criacao_listando_os_disponiveis(
    make_settings: MakeSettings,
) -> None:
    settings = make_settings(
        llm_provider="fornecedor-inexistente",
        llm_api_key="chave-de-teste",
        llm_base_url="https://api.exemplo.invalid/v1",
    )

    with pytest.raises(ValueError, match="Disponiveis: http, mock"):
        get_llm_provider(settings)


def test_provedor_remoto_sem_chave_e_reprovado_na_configuracao(
    make_settings: MakeSettings,
) -> None:
    with pytest.raises(ValueError, match="LLM_API_KEY"):
        make_settings(llm_provider="http", llm_base_url="https://api.exemplo.invalid/v1")


def test_provedor_remoto_sem_endpoint_e_reprovado_na_configuracao(
    make_settings: MakeSettings,
) -> None:
    with pytest.raises(ValueError, match="LLM_BASE_URL"):
        make_settings(llm_provider="http", llm_api_key="chave-de-teste")


async def test_mock_responde_sem_chave_e_sem_endpoint(make_settings: MakeSettings) -> None:
    provider = get_llm_provider(make_settings(llm_api_key=None, llm_base_url=None))

    result = await provider.complete("prompt de extracao")

    assert result.provider == "mock"
    assert result.text.strip().startswith("{")


async def test_provedor_sai_do_ambiente_sem_nenhuma_chave_configurada(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cenario da pre-banca: ambiente minimo, sem LLM_API_KEY, respondendo pelo mock."""

    for variavel, valor in {
        "ENVIRONMENT": "development",
        "LOG_LEVEL": "INFO",
        "AI_STRUCTURING_PORT": "8003",
        "PIPELINE_SERVICE_URL": "http://localhost:8001",
        "LLM_MODEL": "mock",
        "LLM_API_KEY": "",
        "LLM_TIMEOUT_SECONDS": "30",
        "LLM_MAX_RETRIES": "2",
        "LLM_TEMPERATURE": "0.2",
    }.items():
        monkeypatch.setenv(variavel, valor)
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    get_settings.cache_clear()

    try:
        provider = get_llm_provider()
        result = await provider.complete(
            "Preciso de um treinamento de seguranca para 40 operadores."
        )
    finally:
        get_settings.cache_clear()

    assert provider.name == "mock"
    assert json.loads(result.text)["tema"]
