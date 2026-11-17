"""Rota de geracao de embeddings dos trechos de uma demanda (card #160, RF29).

    POST /api/v1/demands/{demand_id}/embeddings

Busca os trechos ja persistidos pelo pipeline-service, gera um vetor por
trecho com o provedor configurado (``EMBEDDING_PROVIDER``) e envia o lote de
volta para armazenamento. Rota fina: a logica mora em
``app.services.embedding_service``.
"""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.clients.pipeline_client import PipelineServiceClient
from app.core.config import Settings, get_settings
from app.providers.embedding_factory import get_embedding_provider
from app.schemas.embeddings import EmbeddingRunRead
from app.services.embedding_service import EmbeddingService

router = APIRouter(tags=["embeddings"])


def get_embedding_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> EmbeddingService:
    """Monta o caso de uso com o provedor indicado por ``EMBEDDING_PROVIDER``."""

    provider = get_embedding_provider(settings)
    client = PipelineServiceClient(settings.pipeline_service_url)
    return EmbeddingService(provider, client)


@router.post(
    "/demands/{demand_id}/embeddings",
    response_model=EmbeddingRunRead,
    summary="Gerar e armazenar os embeddings dos trechos de uma demanda",
    response_description="Quantos trechos foram embeddados e com qual modelo.",
)
async def embed_demand(
    demand_id: str,
    service: Annotated[EmbeddingService, Depends(get_embedding_service)],
) -> EmbeddingRunRead:
    resultado = await service.embed_demand(demand_id)
    return EmbeddingRunRead.from_result(resultado)
