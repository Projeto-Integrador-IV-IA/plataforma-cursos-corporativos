"""Login e verificacao de sessao (RF26 consolidado; RF16 na matriz).

A resposta de login invalido nao distingue e-mail inexistente de senha errada.

"""

from collections.abc import Iterator
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, status

from app.auth.dependencies import CurrentUser
from app.core.config import Settings, get_settings
from app.schemas.auth import (
    ErrorResponse,
    LoginRequest,
    OperatorInfo,
    SessionResponse,
    TokenResponse,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


def get_auth_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> Iterator[AuthService]:
    with httpx.Client(base_url=settings.pipeline_service_url, timeout=5.0) as client:
        yield AuthService(client, settings)


@router.post(
    "/login",
    response_model=TokenResponse,
    responses={status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse}},
)
def login(
    data: LoginRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenResponse:
    return service.login(data)


@router.get(
    "/verify",
    response_model=SessionResponse,
    responses={status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse}},
)
def verify_session(user: CurrentUser) -> SessionResponse:
    return SessionResponse(
        operator=OperatorInfo(id=user.id, name=user.name, email=user.email, role=user.role)
    )
