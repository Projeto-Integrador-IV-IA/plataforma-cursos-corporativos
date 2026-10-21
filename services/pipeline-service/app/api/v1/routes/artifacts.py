"""Persistencia e consulta dos resultados bruto e estruturado da IA, e restauracao de versoes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Path, status
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.schemas.artifact import (
    ArtifactErrorResponse,
    ArtifactRead,
    ArtifactResultCreate,
    ArtifactVersionRead,
)
from app.services.artifact_service import ArtifactService

router = APIRouter(tags=["artifacts"])


@router.post(
    "/demands/{demand_id}/artifacts",
    response_model=ArtifactRead,
    status_code=status.HTTP_201_CREATED,
    summary="Persistir resultado da IA",
    description=(
        "Grava atomicamente a resposta bruta, o resultado estruturado validado e os vinculos "
        "com todas as fontes da demanda usadas pela IA."
    ),
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": ArtifactErrorResponse,
            "description": "Demanda ou fonte inexistente.",
        },
        status.HTTP_409_CONFLICT: {
            "model": ArtifactErrorResponse,
            "description": "Fonte de outra demanda ou conflito de persistencia.",
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "model": ArtifactErrorResponse,
            "description": "Resultado ou identificadores invalidos.",
        },
    },
)
def create_artifact_result(
    demand_id: UUID,
    data: ArtifactResultCreate,
    session: Annotated[Session, Depends(get_session)],
) -> ArtifactRead:
    return ArtifactService(session).create_result(demand_id, data)


@router.get(
    "/demands/{demand_id}/artifacts",
    response_model=list[ArtifactRead],
    summary="Consultar resultados da demanda",
    description=(
        "Recupera resultados brutos e estruturados com as fontes que originaram cada artefato."
    ),
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": ArtifactErrorResponse,
            "description": "Demanda inexistente.",
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "model": ArtifactErrorResponse,
            "description": "Identificador invalido.",
        },
    },
)
def list_demand_artifacts(
    demand_id: UUID,
    session: Annotated[Session, Depends(get_session)],
) -> list[ArtifactRead]:
    return ArtifactService(session).list_by_demand(demand_id)


@router.post(
    "/artifacts/{artifact_id}/versions/{number}/restore",
    response_model=ArtifactVersionRead,
    status_code=status.HTTP_201_CREATED,
    summary="Restaurar uma versao anterior do artefato",
    description=(
        "Cria uma versao nova, vigente, com o conteudo da versao escolhida. Nenhuma versao "
        "existente e alterada: o historico intermediario continua consultavel. A versao nova "
        "registra qual versao foi restaurada e o autor, lido do cabecalho X-User-ID."
    ),
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": ArtifactErrorResponse,
            "description": "Artefato, versao ou operador inexistente.",
        },
        status.HTTP_409_CONFLICT: {
            "model": ArtifactErrorResponse,
            "description": "A versao escolhida ja e a vigente.",
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "model": ArtifactErrorResponse,
            "description": "Identificador ou numero de versao invalido.",
        },
    },
)
def restore_artifact_version(
    artifact_id: UUID,
    number: Annotated[int, Path(ge=1, description="Numero da versao a restaurar.")],
    author_id: Annotated[UUID, Header(alias="X-User-ID")],
    session: Annotated[Session, Depends(get_session)],
) -> ArtifactVersionRead:
    return ArtifactService(session).restore_version(artifact_id, number, author_id)
