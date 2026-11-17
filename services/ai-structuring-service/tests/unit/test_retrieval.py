"""Recuperacao por similaridade no contexto do prompt (RF29, cards #161/#162).

O que estes testes protegem: com a recuperacao desligada (padrao) ou sem como
recuperar, o comportamento de sempre - texto completo - continua intacto; com
a recuperacao ligada e a demanda tendo embedding gravado, o prompt enviado ao
provedor usa os trechos recuperados, ja truncados pelo teto de tamanho, no
lugar do texto inteiro.
"""

import json
from typing import Any

from app.providers import CompletionResult, LLMProvider
from app.providers.mock_provider import RESPOSTA_FIXA
from app.services.structuring_service import RawDemand, StructuringService
from tests.conftest import MakeSettings

RESPOSTA_VALIDA = json.dumps(RESPOSTA_FIXA)

DEMANDA = RawDemand(
    demand_id="dem-retrieval-1",
    text="linha um da demanda\nlinha dois da demanda\nlinha tres da demanda",
)


class _ProviderQueCapturaOPrompt(LLMProvider):
    """Devolve sempre uma resposta valida, guardando o prompt recebido."""

    name = "captura"

    def __init__(self) -> None:
        self.prompts: list[str] = []

    async def complete(self, prompt: str, params: object | None = None) -> CompletionResult:
        self.prompts.append(prompt)
        return CompletionResult(text=RESPOSTA_VALIDA, provider=self.name, model="captura-1")


class _EmbeddingProviderFalso:
    name = "mock"
    dimension = 3

    async def embed(self, texts: list[str]):
        from app.providers.embedding_base import EmbeddingResult

        return EmbeddingResult(
            vectors=tuple((1.0, 0.0, 0.0) for _ in texts),
            provider=self.name,
            model="modelo-de-busca",
            dimension=3,
        )


class _PipelineClientFalso:
    def __init__(self, resultados: list[dict[str, Any]] | None = None, falhar: bool = False):
        self._resultados = resultados if resultados is not None else []
        self._falhar = falhar
        self.chamadas: list[dict[str, Any]] = []

    async def search_similar_segments(
        self, demand_id: str, *, model: str, vector: list[float], top_k: int, min_similarity: float
    ) -> list[dict[str, Any]]:
        if self._falhar:
            raise RuntimeError("pipeline-service indisponivel")
        self.chamadas.append(
            {
                "demand_id": demand_id,
                "model": model,
                "top_k": top_k,
                "min_similarity": min_similarity,
            }
        )
        return self._resultados


def _montar(
    make_settings: MakeSettings,
    provider: LLMProvider,
    *,
    pipeline_client: object | None = None,
    embedding_provider: object | None = None,
    **overrides: object,
) -> StructuringService:
    base: dict[str, object] = {"llm_max_retries": 0, "llm_schema_max_retries": 0}
    base.update(overrides)
    return StructuringService(
        provider,
        make_settings(**base),
        embedding_provider=embedding_provider,
        pipeline_client=pipeline_client,
    )


async def test_retrieval_disabled_by_default_uses_full_text(make_settings: MakeSettings) -> None:
    provider = _ProviderQueCapturaOPrompt()
    service = _montar(
        make_settings,
        provider,
        pipeline_client=_PipelineClientFalso(resultados=[{"content": "nao deveria aparecer"}]),
        embedding_provider=_EmbeddingProviderFalso(),
        retrieval_enabled=False,
    )

    await service.structure_course(DEMANDA)

    assert "linha um da demanda" in provider.prompts[0]
    assert "nao deveria aparecer" not in provider.prompts[0]


async def test_retrieval_enabled_without_provider_or_client_falls_back_to_full_text(
    make_settings: MakeSettings,
) -> None:
    provider = _ProviderQueCapturaOPrompt()
    service = _montar(make_settings, provider, retrieval_enabled=True)

    await service.structure_course(DEMANDA)

    assert "linha um da demanda" in provider.prompts[0]


async def test_retrieval_enabled_with_results_uses_retrieved_segments(
    make_settings: MakeSettings,
) -> None:
    provider = _ProviderQueCapturaOPrompt()
    cliente = _PipelineClientFalso(
        resultados=[
            {"content": "trecho recuperado mais relevante"},
            {"content": "trecho recuperado em segundo lugar"},
        ]
    )
    service = _montar(
        make_settings,
        provider,
        pipeline_client=cliente,
        embedding_provider=_EmbeddingProviderFalso(),
        retrieval_enabled=True,
        retrieval_top_k=2,
        retrieval_min_similarity=0.1,
    )

    await service.structure_course(DEMANDA)

    prompt = provider.prompts[0]
    assert "trecho recuperado mais relevante" in prompt
    assert "trecho recuperado em segundo lugar" in prompt
    assert "linha um da demanda" not in prompt
    assert cliente.chamadas[0]["top_k"] == 2
    assert cliente.chamadas[0]["min_similarity"] == 0.1
    assert cliente.chamadas[0]["model"] == "modelo-de-busca"


async def test_retrieval_enabled_without_any_match_falls_back_to_full_text(
    make_settings: MakeSettings,
) -> None:
    provider = _ProviderQueCapturaOPrompt()
    service = _montar(
        make_settings,
        provider,
        pipeline_client=_PipelineClientFalso(resultados=[]),
        embedding_provider=_EmbeddingProviderFalso(),
        retrieval_enabled=True,
    )

    await service.structure_course(DEMANDA)

    assert "linha um da demanda" in provider.prompts[0]


async def test_retrieval_failure_falls_back_to_full_text_without_raising(
    make_settings: MakeSettings,
) -> None:
    provider = _ProviderQueCapturaOPrompt()
    service = _montar(
        make_settings,
        provider,
        pipeline_client=_PipelineClientFalso(falhar=True),
        embedding_provider=_EmbeddingProviderFalso(),
        retrieval_enabled=True,
    )

    outcome = await service.structure_course(DEMANDA)

    assert outcome.error is None
    assert "linha um da demanda" in provider.prompts[0]


async def test_retrieval_context_is_truncated_by_character_budget(
    make_settings: MakeSettings,
) -> None:
    provider = _ProviderQueCapturaOPrompt()
    trecho_grande = "x" * 50
    cliente = _PipelineClientFalso(
        resultados=[
            {"content": trecho_grande},
            {"content": trecho_grande},
            {"content": trecho_grande},
        ]
    )
    service = _montar(
        make_settings,
        provider,
        pipeline_client=cliente,
        embedding_provider=_EmbeddingProviderFalso(),
        retrieval_enabled=True,
        # So cabem 2 trechos de 50 caracteres dentro do teto de 120.
        retrieval_max_context_chars=120,
    )

    await service.structure_course(DEMANDA)

    prompt = provider.prompts[0]
    assert prompt.count(trecho_grande) == 2
