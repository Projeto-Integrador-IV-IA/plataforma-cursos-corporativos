"""Rotas de persistencia e consulta dos trechos citaveis das fontes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.schemas.segment import (
    SourceSegmentBatchCreate,
    SourceSegmentErrorResponse,
    SourceSegmentRead,
)
from app.services.segment_service import SourceSegmentService

router = APIRouter(tags=["source-segments"])


@router.post(
    "/raw-inputs/{raw_input_id}/segments",
    response_model=list[SourceSegmentRead],
    status_code=status.HTTP_201_CREATED,
    summary="Persistir trechos de uma fonte",
    description=(
        "Persiste atomicamente os trechos identificados pelo ingestion-service. "
        "Repetir o mesmo lote e idempotente; IDs ou posicoes divergentes sao recusados."
    ),
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": SourceSegmentErrorResponse,
            "description": "Fonte bruta inexistente.",
        },
        status.HTTP_409_CONFLICT: {
            "model": SourceSegmentErrorResponse,
            "description": "ID ou posicao ja vinculada a outro trecho.",
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "model": SourceSegmentErrorResponse,
            "description": "Lote ou identificador invalido.",
        },
    },
)
def persist_source_segments(
    raw_input_id: UUID,
    data: SourceSegmentBatchCreate,
    session: Annotated[Session, Depends(get_session)],
) -> list[SourceSegmentRead]:
    return SourceSegmentService(session).persist(raw_input_id, data)


@router.get(
    "/raw-inputs/{raw_input_id}/segments",
    response_model=list[SourceSegmentRead],
    summary="Consultar trechos por fonte",
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": SourceSegmentErrorResponse,
            "description": "Fonte bruta inexistente.",
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "model": SourceSegmentErrorResponse,
            "description": "Identificador invalido.",
        },
    },
)
def list_source_segments(
    raw_input_id: UUID,
    session: Annotated[Session, Depends(get_session)],
) -> list[SourceSegmentRead]:
    return SourceSegmentService(session).list_by_source(raw_input_id)


@router.get(
    "/demands/{demand_id}/segments",
    response_model=list[SourceSegmentRead],
    summary="Consultar trechos por demanda",
    description="Recupera, em ordem deterministica, os trechos de todas as fontes da demanda.",
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": SourceSegmentErrorResponse,
            "description": "Demanda inexistente.",
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "model": SourceSegmentErrorResponse,
            "description": "Identificador invalido.",
        },
    },
)
def list_demand_segments(
    demand_id: UUID,
    session: Annotated[Session, Depends(get_session)],
) -> list[SourceSegmentRead]:
    return SourceSegmentService(session).list_by_demand(demand_id)
