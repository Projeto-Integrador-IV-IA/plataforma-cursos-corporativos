"""Testes do provedor mock: resposta fixa, sem rede e sem chave (RNF12)."""

import json

import pytest

from app.core.exceptions import LLMRateLimitError, LLMTimeoutError
from app.providers import CompletionParams, LLMProvider, MockLLMProvider
from app.providers.mock_provider import RESPOSTA_FIXA

CAMPOS_EXTRAIDOS = (
    "tema",
    "nicho",
    "publico_alvo",
    "numero_participantes",
    "carga_horaria",
    "formato",
)
CAMPOS_GERADOS = ("objetivos_aprendizagem", "ementa")


def test_mock_cumpre_o_contrato_do_provedor() -> None:
    assert isinstance(MockLLMProvider(), LLMProvider)
    assert MockLLMProvider.name == "mock"


async def test_resposta_traz_os_campos_do_curso_estruturado() -> None:
    result = await MockLLMProvider().complete("qualquer prompt")

    curso = json.loads(result.text)

    for campo in CAMPOS_EXTRAIDOS + CAMPOS_GERADOS:
        assert campo in curso, campo
    assert curso["campos_ausentes"] == RESPOSTA_FIXA["campos_ausentes"]
    assert len(curso["ementa"]) == 3


async def test_carga_horaria_dos_modulos_fecha_com_a_carga_total() -> None:
    curso = json.loads((await MockLLMProvider().complete("prompt")).text)

    soma = sum(modulo["carga_horaria"] for modulo in curso["ementa"])

    assert soma == curso["carga_horaria"]


async def test_resposta_e_deterministica_entre_chamadas_e_prompts() -> None:
    provider = MockLLMProvider()

    primeira = await provider.complete("prompt de extracao")
    segunda = await provider.complete("prompt completamente diferente")

    assert primeira.text == segunda.text


async def test_metadados_de_execucao_sao_preenchidos() -> None:
    result = await MockLLMProvider().complete("prompt de extracao")

    assert result.provider == "mock"
    assert result.model == "mock"
    assert result.finish_reason == "stop"
    assert result.usage.prompt_tokens > 0
    assert result.usage.completion_tokens > 0
    assert result.latency_ms >= 0


async def test_modelo_dos_parametros_prevalece_nos_metadados() -> None:
    result = await MockLLMProvider(model="mock-a").complete("p", CompletionParams(model="mock-b"))

    assert result.model == "mock-b"


async def test_texto_de_resposta_pode_ser_substituido_para_um_cenario_de_teste() -> None:
    provider = MockLLMProvider(response_text="{}")

    assert (await provider.complete("prompt")).text == "{}"


@pytest.mark.parametrize(
    "falha",
    [LLMTimeoutError(timeout_seconds=15.0), LLMRateLimitError(retry_after_seconds=5.0)],
)
async def test_mock_reproduz_caminho_de_falha_de_forma_deterministica(falha: Exception) -> None:
    provider = MockLLMProvider(fail_with=falha)  # type: ignore[arg-type]

    with pytest.raises(type(falha)):
        await provider.complete("prompt")
