"""Porta de entrada padronizada para texto bruto multicanal (RF09)."""

from collections.abc import Iterator
from typing import Annotated
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, File, Form, Header, Request, UploadFile, status
from starlette.concurrency import run_in_threadpool

from app.clients.pipeline_client import PipelineClient
from app.core.config import Settings, get_settings
from app.schemas.ingestion import AudioIngestionRead, ErrorResponse, IngestionCreate, IngestionRead
from app.services.audio_validation import validate_audio
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
            "description": "Demanda, operador ou tentativa anterior inexistente.",
        },
        status.HTTP_409_CONFLICT: {
            "model": ErrorResponse,
            "description": "Referencia removida ou tentativa anterior de outra demanda.",
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


@router.post(
    "/audio",
    response_model=AudioIngestionRead,
    status_code=201,
    summary="Captar arquivo de audio como fonte da demanda",
    description=(
        "Valida formato, tamanho e duracao e persiste o arquivo original e a "
        "proveniencia antes de qualquer transcricao. STT permanece PENDENTE (card #165)."
    ),
    responses={
        code: {"model": ErrorResponse, "description": description}
        for code, description in {
            404: "Demanda ou operador inexistente.",
            409: "Conflito de referencia durante a persistencia.",
            413: "Audio excede o tamanho maximo configurado.",
            422: "Audio, duracao ou identificadores invalidos.",
            502: "Pipeline indisponivel ou confirmacao invalida.",
            504: "Timeout ao confirmar persistencia do audio.",
        }.items()
    },
)
async def capture_audio(
    request: Request,
    file: Annotated[UploadFile, File(description="Arquivo WAV, MP3, M4A, OGG ou FLAC.")],
    demand_id: Annotated[UUID, Form()],
    author_id: Annotated[UUID, Header(alias="X-User-ID")],
    settings: Annotated[Settings, Depends(get_settings)],
    pipeline: Annotated[PipelineClient, Depends(get_pipeline_client)],
) -> AudioIngestionRead:
    try:
        content = await file.read(settings.audio_max_bytes + 1)
        audio = await run_in_threadpool(
            validate_audio,
            demand_id=demand_id,
            filename=file.filename,
            content_type=file.content_type,
            content=content,
            settings=settings,
        )
    finally:
        await file.close()
    receipt = await run_in_threadpool(
        pipeline.persist_audio,
        audio,
        author_id=author_id,
        request_id=request.headers.get("X-Request-ID"),
    )
    return AudioIngestionRead(
        raw_input_id=receipt.id,
        demand_id=receipt.demand_id,
        author_id=receipt.author_id,
        received_order=receipt.received_order,
        created_at=receipt.created_at,
        audio=receipt.audio,
    )
