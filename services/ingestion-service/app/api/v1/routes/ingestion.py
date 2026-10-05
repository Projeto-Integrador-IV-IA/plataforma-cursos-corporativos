"""Porta de entrada padronizada para texto bruto multicanal (RF09)."""

from collections.abc import Iterator
from typing import Annotated
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, Header, Request, status

from app.clients.pipeline_client import PipelineClient
from app.core.config import Settings, get_settings
from app.schemas.ingestion import ErrorResponse, IngestionCreate, IngestionRead
from app.services.ingestion_service import IngestionService

router = APIRouter(prefix="/ingestion", tags=["ingestion"])


def get_pipeline_client(
    settings: Annotated[Settings, Depends(get_settings)],
) -> Iterator[PipelineClient]:
    with httpx.Client(
        base_url=settings.pipeline_service_url,
        timeout=settings.pipeline_timeout_seconds,
    ) as http_client:
        yield PipelineClient(http_client)


def get_ingestion_service(
    pipeline_client: Annotated[PipelineClient, Depends(get_pipeline_client)],
) -> IngestionService:
    return IngestionService(pipeline_client)


@router.post(
    "",
    response_model=IngestionRead,
    status_code=status.HTTP_201_CREATED,
    summary="Captar texto bruto multicanal",
    description=(
        "Persiste o texto original no pipeline-service e somente entao confirma a captacao. "
        "Nenhuma normalizacao ou chamada a IA ocorre antes desse commit."
    ),
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponse,
            "description": "Demanda ou operador inexistente.",
        },
        status.HTTP_409_CONFLICT: {
            "model": ErrorResponse,
            "description": "Referencia removida durante a persistencia.",
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "model": ErrorResponse,
            "description": "Texto, origem, demanda ou operador invalido.",
        },
        status.HTTP_502_BAD_GATEWAY: {
            "model": ErrorResponse,
            "description": "Falha de comunicacao ou resposta invalida do pipeline-service.",
        },
        status.HTTP_504_GATEWAY_TIMEOUT: {
            "model": ErrorResponse,
            "description": "Timeout ao persistir no pipeline-service.",
        },
    },
)
def capture_raw_text(
    payload: IngestionCreate,
    author_id: Annotated[UUID, Header(alias="X-User-ID")],
    request: Request,
    service: Annotated[IngestionService, Depends(get_ingestion_service)],
) -> IngestionRead:
    persisted = service.capture(
        payload.to_domain(),
        author_id=author_id,
        request_id=request.headers.get("X-Request-ID"),
    )
    return IngestionRead.from_domain(persisted)
