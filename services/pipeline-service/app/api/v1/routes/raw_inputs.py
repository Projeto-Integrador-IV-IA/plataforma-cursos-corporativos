"""Rota interna de persistencia das fontes brutas captadas pelo RF09."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.schemas.raw_input import RawInputCreate, RawInputErrorResponse, RawInputRead
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
            "description": "Demanda ou operador inexistente.",
        },
        status.HTTP_409_CONFLICT: {
            "model": RawInputErrorResponse,
            "description": "Referencia removida durante a persistencia.",
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
