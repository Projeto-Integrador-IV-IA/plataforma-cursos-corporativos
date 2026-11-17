"""Testes do caso de uso de embeddagem de uma demanda (card #160, RF29).

O que estes testes protegem: demanda sem trecho persistido nao falha, so
nao embedda nada; demanda com trecho gera um vetor por trecho e envia o lote
inteiro, com o segment_id e o modelo corretos, para o pipeline-service.
"""

from typing import Any

from app.providers.mock_embedding_provider import MockEmbeddingProvider
from app.services.embedding_service import EmbeddingService


class _ClientFalso:
    """Dubla do PipelineServiceClient: guarda o que recebeu, sem rede."""

    def __init__(self, segmentos: list[dict[str, Any]]) -> None:
        self._segmentos = segmentos
        self.lotes_enviados: list[list[dict[str, Any]]] = []

    async def list_demand_segments(self, demand_id: str) -> list[dict[str, Any]]:
        return self._segmentos

    async def save_segment_embeddings(self, embeddings: list[dict[str, Any]]) -> None:
        self.lotes_enviados.append(embeddings)


def _segmento(segment_id: str, content: str) -> dict[str, Any]:
    return {"id": segment_id, "content": content}


async def test_demand_without_persisted_segments_embeds_nothing() -> None:
    cliente = _ClientFalso(segmentos=[])
    service = EmbeddingService(MockEmbeddingProvider(), cliente)

    resultado = await service.embed_demand("dem-sem-trecho")

    assert resultado.segments_embedded == 0
    assert cliente.lotes_enviados == []


async def test_demand_with_segments_sends_one_vector_per_segment() -> None:
    segmentos = [_segmento("seg-1", "primeiro trecho"), _segmento("seg-2", "segundo trecho")]
    cliente = _ClientFalso(segmentos=segmentos)
    provider = MockEmbeddingProvider(model="modelo-de-teste")
    service = EmbeddingService(provider, cliente)

    resultado = await service.embed_demand("dem-42")

    assert resultado.segments_embedded == 2
    assert resultado.model == "modelo-de-teste"
    assert len(cliente.lotes_enviados) == 1
    lote = cliente.lotes_enviados[0]
    assert [item["segment_id"] for item in lote] == ["seg-1", "seg-2"]
    assert all(item["model"] == "modelo-de-teste" for item in lote)
    assert all(isinstance(item["vector"], list) and item["vector"] for item in lote)


async def test_different_segments_get_different_vectors() -> None:
    segmentos = [_segmento("seg-1", "conteudo A"), _segmento("seg-2", "conteudo completamente B")]
    cliente = _ClientFalso(segmentos=segmentos)
    service = EmbeddingService(MockEmbeddingProvider(), cliente)

    await service.embed_demand("dem-42")

    lote = cliente.lotes_enviados[0]
    assert lote[0]["vector"] != lote[1]["vector"]
