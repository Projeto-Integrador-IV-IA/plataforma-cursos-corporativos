"""Testes do provedor de embedding mock e da fabrica (card #160, RF29)."""

import pytest

from app.providers.embedding_factory import get_embedding_provider
from app.providers.mock_embedding_provider import MockEmbeddingProvider


async def test_mock_provider_is_deterministic() -> None:
    provider = MockEmbeddingProvider()

    primeira = await provider.embed(["mesmo texto"])
    segunda = await provider.embed(["mesmo texto"])

    assert primeira.vectors == segunda.vectors


async def test_mock_provider_distinguishes_different_texts() -> None:
    provider = MockEmbeddingProvider()

    resultado = await provider.embed(["texto a", "texto b"])

    assert resultado.vectors[0] != resultado.vectors[1]


async def test_mock_provider_preserves_order_and_count() -> None:
    provider = MockEmbeddingProvider()

    resultado = await provider.embed(["um", "dois", "tres"])

    assert len(resultado.vectors) == 3
    assert all(len(vetor) == provider.dimension for vetor in resultado.vectors)


async def test_mock_provider_reports_its_own_model_name() -> None:
    provider = MockEmbeddingProvider(model="um-modelo-de-teste")

    resultado = await provider.embed(["texto"])

    assert resultado.model == "um-modelo-de-teste"
    assert resultado.provider == "mock"


def test_factory_builds_mock_provider_by_name(make_settings) -> None:  # type: ignore[no-untyped-def]
    settings = make_settings(embedding_provider="mock", embedding_model="modelo-x")

    provider = get_embedding_provider(settings)

    assert isinstance(provider, MockEmbeddingProvider)
    assert provider.model == "modelo-x"


def test_factory_rejects_unknown_provider_name(make_settings) -> None:  # type: ignore[no-untyped-def]
    settings = make_settings(embedding_provider="inexistente")

    with pytest.raises(ValueError, match="inexistente"):
        get_embedding_provider(settings)
