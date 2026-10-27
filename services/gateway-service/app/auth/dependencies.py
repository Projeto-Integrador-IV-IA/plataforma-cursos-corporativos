"""Dependencias de autenticacao das rotas (RF26 e RNF18 consolidados).

Fornece a dependencia que extrai e valida o token do header Authorization e
disponibiliza o usuario autenticado para a rota.

Cada operacao protegida declara ``CurrentUser`` e recebe a identidade somente
depois que o gateway valida o Bearer JWT.

"""

from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.jwt import AuthenticatedUser, InvalidAccessTokenError, decode_access_token
from app.core.config import Settings, get_settings
from app.core.exceptions import UnauthorizedError

_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthenticatedUser:
    """Recusa por padrao requisicoes sem um Bearer JWT valido."""

    if credentials is None or credentials.scheme.casefold() != "bearer":
        raise UnauthorizedError()
    try:
        return decode_access_token(credentials.credentials, settings)
    except InvalidAccessTokenError as exc:
        raise UnauthorizedError() from exc


CurrentUser = Annotated[AuthenticatedUser, Depends(get_current_user)]
