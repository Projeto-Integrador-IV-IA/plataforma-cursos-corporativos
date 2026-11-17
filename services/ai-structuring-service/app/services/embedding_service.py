"""Caso de uso: gerar e armazenar embeddings dos trechos de uma demanda (card #160, RF29).

Fluxo: busca os trechos ja persistidos pelo pipeline-service, gera um vetor
por trecho com o provedor configurado (``EMBEDDING_PROVIDER``) e envia o lote
de volta para armazenamento - o pipeline-service e quem guarda e indexa
(ADR-0001, ADR-0007).

Demanda sem trecho persistido (ninguem chamou a captacao de trechos ainda, ou
a demanda nao tem fonte) nao e erro: devolve zero embeddings gerados, e quem
chamou decide se tenta de novo depois.
"""

import logging
from dataclasses import dataclass

from app.clients.pipeline_client import PipelineServiceClient
from app.providers.embedding_base import EmbeddingProvider

_logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class EmbeddingRunResult:
    """Desfecho de uma rodada de embeddagem de uma demanda.

    Attributes:
        demand_id: demanda cujos trechos foram embeddados.
        model: modelo de embedding usado, para o registro de proveniencia
            (RNF08) - e o mesmo valor que vai para ``SegmentEmbeddingCreate.model``.
        segments_embedded: quantos trechos tinham conteudo e foram enviados
            para armazenamento. Zero quando a demanda nao tem trecho
            persistido ainda.
    """

    demand_id: str
    model: str
    segments_embedded: int


class EmbeddingService:
    """Gera embeddings dos trechos de uma demanda e os envia para armazenamento."""

    def __init__(
        self,
        provider: EmbeddingProvider,
        pipeline_client: PipelineServiceClient,
    ) -> None:
        self._provider = provider
        self._pipeline_client = pipeline_client

    async def embed_demand(self, demand_id: str) -> EmbeddingRunResult:
        """Busca, gera e persiste os embeddings dos trechos da demanda (card #160).

        Args:
            demand_id: identificador da demanda cujos trechos (ja persistidos
                por ``source_segments``) serao embeddados.

        Returns:
            ``EmbeddingRunResult`` com quantos trechos foram processados.
        """

        segmentos = await self._pipeline_client.list_demand_segments(demand_id)
        if not segmentos:
            _logger.info(
                "Nenhum trecho persistido para a demanda (demand_id=%s); nada a embeddar.",
                demand_id,
            )
            return EmbeddingRunResult(
                demand_id=demand_id, model=self._provider.name, segments_embedded=0
            )

        textos = [segmento["content"] for segmento in segmentos]
        resultado = await self._provider.embed(textos)

        payload = [
            {
                "segment_id": segmento["id"],
                "model": resultado.model,
                "vector": list(vetor),
            }
            for segmento, vetor in zip(segmentos, resultado.vectors, strict=True)
        ]
        await self._pipeline_client.save_segment_embeddings(payload)

        _logger.info(
            "Embeddings gerados e enviados (demand_id=%s, modelo=%s, trechos=%d).",
            demand_id,
            resultado.model,
            len(payload),
        )
        return EmbeddingRunResult(
            demand_id=demand_id, model=resultado.model, segments_embedded=len(payload)
        )
