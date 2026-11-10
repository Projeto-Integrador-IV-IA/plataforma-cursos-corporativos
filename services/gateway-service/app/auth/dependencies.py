"""Dependencias de autenticacao das rotas (RF26 e RNF18 consolidados).

Fornece a dependencia que extrai e valida o token do header Authorization e
disponibiliza o usuario autenticado para a rota.

Cada operacao protegida declara ``CurrentUser`` e recebe a identidade somente
depois que o gateway valida o Bearer JWT.

"""

from dataclasses import replace
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.jwt import AuthenticatedUser, InvalidAccessTokenError, decode_access_token
from app.core.config import Settings, get_settings
from app.core.exceptions import UnauthorizedError
from app.services.auth_service import Permission, normalize_role, role_has_permission

_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthenticatedUser:
    """Recusa por padrao requisicoes sem um Bearer JWT valido."""

    if credentials is None or credentials.scheme.casefold() != "bearer":
        raise UnauthorizedError()
    try:
        user = decode_access_token(credentials.credentials, settings)
        return replace(user, role=normalize_role(user.role).value)
    except InvalidAccessTokenError as exc:
        raise UnauthorizedError() from exc


CurrentUser = Annotated[AuthenticatedUser, Depends(get_current_user)]


def require_permission(permission: str | Permission):
    """Cria uma dependencia que exige uma permissao da matriz de acesso."""

    def dependency(user: CurrentUser) -> AuthenticatedUser:
        if not role_has_permission(user.role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Perfil sem permissao para esta operacao.",
            )
        return user

    return dependency


def require_any_permission(*permissions: str | Permission):
    """Cria uma dependencia para rotas que aceitam qualquer permissao listada."""

    def dependency(user: CurrentUser) -> AuthenticatedUser:
        if not any(role_has_permission(user.role, permission) for permission in permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Perfil sem permissao para esta operacao.",
            )
        return user

    return dependency
