"""Persistencia e consulta dos resultados bruto e estruturado da IA."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.schemas.artifact import ArtifactErrorResponse, ArtifactRead, ArtifactResultCreate
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
