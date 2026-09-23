"""Testes do contrato do provedor de LLM (RNF03)."""

import pytest

from app.core.exceptions import LLMTimeoutError
from app.providers import (
    CompletionParams,
    CompletionResult,
    CompletionUsage,
    LLMProvider,
)


class _FakeProvider(LLMProvider):
    """Implementacao minima usada apenas para exercitar o contrato."""

    name = "fake"

    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.calls: list[tuple[str, CompletionParams | None]] = []

    async def complete(
        self,
        prompt: str,
        params: CompletionParams | None = None,
    ) -> CompletionResult:
        self.calls.append((prompt, params))
        if self.fail:
            raise LLMTimeoutError(timeout_seconds=15.0, provider=self.name)
        return CompletionResult(
            text='{"tema": "seguranca do trabalho"}',
            provider=self.name,
            model=(params.model if params else None) or "fake-model",
            usage=CompletionUsage(prompt_tokens=120, completion_tokens=45),
            latency_ms=812.5,
            finish_reason="stop",
        )


def test_provider_abstrato_nao_pode_ser_instanciado() -> None:
    with pytest.raises(TypeError):
        LLMProvider()  # type: ignore[abstract]


def test_subclasse_sem_complete_nao_pode_ser_instanciada() -> None:
    class _Incompleto(LLMProvider):
        name = "incompleto"

    with pytest.raises(TypeError):
        _Incompleto()  # type: ignore[abstract]


async def test_complete_devolve_texto_bruto_e_metadados_de_execucao() -> None:
    provider = _FakeProvider()

    result = await provider.complete("prompt de extracao", CompletionParams(model="modelo-x"))

    assert result.text == '{"tema": "seguranca do trabalho"}'
    assert result.provider == "fake"
    assert result.model == "modelo-x"
    assert result.usage.total_tokens == 165
    assert result.latency_ms == 812.5


async def test_complete_aceita_chamada_sem_parametros() -> None:
    provider = _FakeProvider()

    result = await provider.complete("prompt de extracao")

    assert provider.calls == [("prompt de extracao", None)]
    assert result.model == "fake-model"


async def test_falha_do_provedor_chega_como_excecao_tipada() -> None:
    provider = _FakeProvider(fail=True)

    with pytest.raises(LLMTimeoutError) as excinfo:
        await provider.complete("prompt de extracao")

    assert excinfo.value.details["provider"] == "fake"
    assert excinfo.value.details["timeout_seconds"] == 15.0


def test_parametros_ausentes_significam_padrao_do_provedor() -> None:
    params = CompletionParams()

    assert params.model is None
    assert params.temperature is None
    assert params.max_output_tokens is None
    assert params.timeout_seconds is None
    assert params.system_prompt is None
    assert params.response_schema is None


def test_resultado_e_imutavel_para_preservar_a_proveniencia() -> None:
    result = CompletionResult(text="ok", provider="fake", model="fake-model")

    with pytest.raises(AttributeError):
        result.text = "outro"  # type: ignore[misc]

    assert result.usage.total_tokens == 0
    assert result.metadata == {}
