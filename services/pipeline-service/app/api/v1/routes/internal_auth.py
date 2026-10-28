"""Consulta interna de credenciais pelo gateway, unico dono da autenticacao."""

import secrets
from typing import Annotated

import sqlalchemy as sa
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import EmailStr
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.session import get_session
from app.models import User
from app.schemas.internal_auth import InternalUserCredentials

router = APIRouter(prefix="/api/v1/internal/auth", tags=["internal-auth"])


def require_auth_service(
    settings: Annotated[Settings, Depends(get_settings)],
    service_key: Annotated[str | None, Header(alias="X-Service-Key")] = None,
) -> None:
    """Aceita somente a chave compartilhada por ambiente com o gateway."""

    if service_key is None or not secrets.compare_digest(
        service_key, settings.auth_service_key.get_secret_value()
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credencial invalida")


@router.get(
    "/users/by-email",
    response_model=InternalUserCredentials,
    dependencies=[Depends(require_auth_service)],
    responses={status.HTTP_404_NOT_FOUND: {"description": "Usuario inexistente."}},
)
def get_user_credentials(
    email: Annotated[EmailStr, Query()],
    session: Annotated[Session, Depends(get_session)],
) -> InternalUserCredentials:
    normalized = str(email).strip().casefold()
    user = session.scalar(sa.select(User).where(sa.func.lower(User.email) == normalized))
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario inexistente")
    return InternalUserCredentials.model_validate(user)
