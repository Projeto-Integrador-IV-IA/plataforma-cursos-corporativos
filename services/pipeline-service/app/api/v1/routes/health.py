"""Endpoints de saude do pipeline-service.

Rotas previstas:
    GET /health   - o processo esta de pe (liveness).
    GET /ready    - as dependencias respondem (readiness): banco, servicos
                    a jusante e provedor de LLM, conforme o caso.

Usados pelo healthcheck do Docker Compose e pela CI. Nao exigem autenticacao e
nao devem revelar detalhes internos de infraestrutura (RNF10).

Implementa liveness e readiness sem expor detalhes da infraestrutura.
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import ServiceUnavailableError
from app.db.session import get_session

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
def readiness(session: Annotated[Session, Depends(get_session)]) -> dict[str, str]:
    try:
        session.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise ServiceUnavailableError(
            code="SERVICE_NOT_READY",
            message="Serviço temporariamente indisponível.",
        ) from exc
    return {"status": "ready"}
