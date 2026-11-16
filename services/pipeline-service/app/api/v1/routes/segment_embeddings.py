"""Rotas de gravacao em lote e busca por similaridade de embeddings de trecho.

RNF28 consolidado.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.schemas.segment_embedding import (
    SegmentEmbeddingBatchCreate,
    SegmentEmbeddingErrorResponse,
    SegmentEmbeddingRead,
    SimilaritySearchRequest,
    SimilaritySearchResponse,
)
from app.services.segment_embedding_service import SegmentEmbeddingService

router = APIRouter(tags=["segment-embeddings"])


@router.post(
    "/segment-embeddings",
    response_model=list[SegmentEmbeddingRead],
    status_code=status.HTTP_201_CREATED,
    summary="Persistir embeddings de trechos ja captados",
    description=(
        "Grava em lote os embeddings gerados pelo ai-structuring-service (card #160) para "
        "trechos ja persistidos (card #158 em services/pipeline-service/app/models). "
        "Append-only: gerar um modelo novo para um trecho ja embeddado soma uma linha, "
        "nunca substitui a existente."
    ),
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": SegmentEmbeddingErrorResponse,
            "description": "Um ou mais trechos nao foram encontrados.",
        },
        status.HTTP_409_CONFLICT: {
            "model": SegmentEmbeddingErrorResponse,
            "description": "Par (trecho, modelo) ja gravado.",
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "model": SegmentEmbeddingErrorResponse,
            "description": "Lote, dimensao do vetor ou identificador invalido.",
        },
    },
)
def create_segment_embeddings(
    data: SegmentEmbeddingBatchCreate,
    session: Annotated[Session, Depends(get_session)],
) -> list[SegmentEmbeddingRead]:
    return SegmentEmbeddingService(session).save_batch(data)


@router.post(
    "/demands/{demand_id}/segment-embeddings/search",
    response_model=SimilaritySearchResponse,
    summary="Buscar trechos da demanda mais proximos de um vetor de consulta",
    description=(
        "Devolve os trechos da demanda mais similares ao vetor de consulta, ordenados do "
        "mais para o menos proximo (card #159). Nunca cruza demanda nem cliente (RNF21)."
    ),
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": SegmentEmbeddingErrorResponse,
            "description": "Demanda inexistente.",
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "model": SegmentEmbeddingErrorResponse,
            "description": "Dimensao do vetor ou parametro de busca invalido.",
        },
    },
)
def search_segment_embeddings(
    demand_id: UUID,
    data: SimilaritySearchRequest,
    session: Annotated[Session, Depends(get_session)],
) -> SimilaritySearchResponse:
    return SegmentEmbeddingService(session).search(demand_id, data)
