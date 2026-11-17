"""Rota interna de persistencia das fontes brutas captadas pelo RF09."""

from hashlib import sha256
from pathlib import PurePosixPath
from typing import Annotated
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Header, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.exceptions import NotFoundError, ValidationError
from app.db.session import get_session
from app.schemas.raw_input import (
    AudioMetadata,
    RawInputCreate,
    RawInputErrorResponse,
    RawInputNormalization,
    RawInputRead,
)
from app.services.raw_input_service import RawInputService

router = APIRouter(tags=["raw-inputs"])


@router.post(
    "/demands/{demand_id}/raw-inputs",
    response_model=RawInputRead,
    status_code=status.HTTP_201_CREATED,
    summary="Persistir texto bruto de uma demanda",
    description=(
        "Rota interna consumida pelo ingestion-service. Confirma a persistencia do conteudo "
        "original antes que qualquer normalizacao ou chamada a IA possa ocorrer."
    ),
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": RawInputErrorResponse,
            "description": "Demanda, operador ou tentativa anterior inexistente.",
        },
        status.HTTP_409_CONFLICT: {
            "model": RawInputErrorResponse,
            "description": "Referencia removida ou tentativa anterior de outra demanda.",
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "model": RawInputErrorResponse,
            "description": "Conteudo, origem ou identificador invalido.",
        },
    },
)
def create_raw_input(
    demand_id: UUID,
    data: RawInputCreate,
    author_id: Annotated[UUID, Header(alias="X-User-ID")],
    session: Annotated[Session, Depends(get_session)],
) -> RawInputRead:
    raw_input = RawInputService(session).create(demand_id, author_id, data)
    return RawInputRead.model_validate(raw_input)


@router.post(
    "/demands/{demand_id}/audio-inputs",
    response_model=RawInputRead,
    status_code=201,
    summary="Persistir arquivo original de audio e proveniencia",
    description=(
        "Rota interna do ingestion-service: recebe arquivo ja validado e duracao "
        "medida na captacao. Confirma commit do binario antes de devolver 201."
    ),
    responses={
        code: {"model": RawInputErrorResponse, "description": message}
        for code, message in {
            404: "Demanda ou operador inexistente.",
            409: "Referencia removida durante a persistencia.",
            422: "Arquivo ou metadados invalidos ou acima dos limites configurados.",
        }.items()
    },
)
def create_audio_input(
    demand_id: UUID,
    file: Annotated[UploadFile, File()],
    duration_seconds: Annotated[float, Form(gt=0, allow_inf_nan=False)],
    author_id: Annotated[UUID, Header(alias="X-User-ID")],
    settings: Annotated[Settings, Depends(get_settings)],
    session: Annotated[Session, Depends(get_session)],
) -> RawInputRead:
    try:
        content = file.file.read(settings.audio_max_bytes + 1)
    finally:
        file.file.close()
    filename = PurePosixPath((file.filename or "").replace("\\", "/")).name
    if not content or len(content) > settings.audio_max_bytes:
        raise ValidationError(
            code="AUDIO_INVALID_SIZE",
            message=f"O audio deve conter de 1 a {settings.audio_max_bytes} bytes.",
        )
    if duration_seconds > settings.audio_max_duration_seconds:
        raise ValidationError(
            code="AUDIO_TOO_LONG",
            message=(
                f"O audio deve durar no maximo {settings.audio_max_duration_seconds:g} segundos."
            ),
        )
    if (
        not filename
        or len(filename) > 255
        or any(ord(char) < 32 for char in filename)
        or file.content_type
        not in {"audio/wav", "audio/mpeg", "audio/mp4", "audio/ogg", "audio/flac"}
    ):
        raise ValidationError(code="AUDIO_INVALID_FORMAT", message="Metadados de audio invalidos.")
    metadata = AudioMetadata(
        filename=filename,
        content_type=file.content_type,
        size_bytes=len(content),
        duration_seconds=duration_seconds,
        sha256=sha256(content).hexdigest(),
    )
    raw_input = RawInputService(session).create_audio(demand_id, author_id, metadata, content)
    session.commit()
    return RawInputRead.model_validate(raw_input)


@router.get(
    "/raw-inputs/{raw_input_id}/audio",
    response_class=Response,
    summary="Recuperar arquivo original de audio",
    responses={
        200: {
            "description": "Bytes originais do arquivo, sem transcodificacao.",
            "content": {
                "application/octet-stream": {"schema": {"type": "string", "format": "binary"}}
            },
        },
        404: {"model": RawInputErrorResponse, "description": "Fonte ou arquivo inexistente."},
    },
)
def download_audio(
    raw_input_id: UUID, session: Annotated[Session, Depends(get_session)]
) -> Response:
    raw_input = RawInputService(session).get(raw_input_id)
    audio = raw_input.audio
    if audio is None:
        raise NotFoundError(code="AUDIO_NOT_FOUND", message="A fonte nao possui arquivo de audio.")
    return Response(
        audio.content,
        media_type=audio.content_type,
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(audio.filename, safe='')}",
            "X-Content-SHA256": audio.sha256,
        },
    )


@router.get(
    "/raw-inputs/{raw_input_id}",
    response_model=RawInputRead,
    summary="Consultar fonte e proveniencia",
    description=(
        "Recupera o conteudo original e a copia normalizada com o canal de origem, "
        "o operador que captou a fonte e a data de recebimento registrada pelo banco."
    ),
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": RawInputErrorResponse,
            "description": "Fonte bruta inexistente.",
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "model": RawInputErrorResponse,
            "description": "Identificador invalido.",
        },
    },
)
def get_raw_input(
    raw_input_id: UUID,
    session: Annotated[Session, Depends(get_session)],
) -> RawInputRead:
    return RawInputRead.model_validate(RawInputService(session).get(raw_input_id))


@router.get(
    "/raw-inputs/{raw_input_id}/attempts",
    response_model=list[RawInputRead],
    summary="Consultar historico de reprocessamento",
    description="Retorna a tentativa inicial e seus reprocessamentos em ordem de recebimento.",
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": RawInputErrorResponse,
            "description": "Fonte bruta inexistente.",
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "model": RawInputErrorResponse,
            "description": "Identificador invalido.",
        },
    },
)
def get_raw_input_attempts(
    raw_input_id: UUID,
    session: Annotated[Session, Depends(get_session)],
) -> list[RawInputRead]:
    attempts = RawInputService(session).list_attempts(raw_input_id)
    return [RawInputRead.model_validate(attempt) for attempt in attempts]


@router.patch(
    "/raw-inputs/{raw_input_id}/normalization",
    response_model=RawInputRead,
    summary="Persistir texto sanitizado",
    description=(
        "Preenche normalized_content depois da persistencia do original. "
        "Esta operacao nunca altera original_content."
    ),
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": RawInputErrorResponse,
            "description": "Fonte bruta inexistente.",
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "model": RawInputErrorResponse,
            "description": "Conteudo normalizado ou identificador invalido.",
        },
    },
)
def normalize_raw_input(
    raw_input_id: UUID,
    data: RawInputNormalization,
    session: Annotated[Session, Depends(get_session)],
) -> RawInputRead:
    raw_input = RawInputService(session).normalize(raw_input_id, data)
    return RawInputRead.model_validate(raw_input)
