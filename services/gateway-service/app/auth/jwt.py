"""Emissao e validacao de token de acesso (RF26).

O gateway e o unico ponto que emite e valida token. Os servicos internos
confiam no gateway e nao reimplementam autenticacao - isso mantem uma unica
superficie de autenticacao para auditar (RNF10).

Contrato previsto:
    - token JWT assinado com ``JWT_SECRET_KEY`` (RNF11), algoritmo e expiracao
      vindos de configuracao;
    - claims minimas: sub (id do usuario), nome, papel, exp, iat;
    - validacao rejeita token expirado, assinatura invalida e claim ausente;
    - o identificador do usuario e propagado aos servicos internos por header,
      para sustentar a autoria da trilha de auditoria (RF07).

"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt

from app.core.config import Settings

_TOKEN_TYPE = "access"
_ISSUER = "gateway-service"


class InvalidAccessTokenError(ValueError):
    """Token ausente de claims, expirado ou com assinatura invalida."""


@dataclass(frozen=True, slots=True)
class AuthenticatedUser:
    id: UUID
    name: str
    email: str
    role: str


def create_access_token(
    user: AuthenticatedUser,
    settings: Settings,
    *,
    now: datetime | None = None,
) -> tuple[str, int]:
    """Emite token assinado com expiracao determinada pela configuracao."""

    issued_at = (now or datetime.now(UTC)).astimezone(UTC)
    expires_in = settings.access_token_expire_minutes * 60
    token = jwt.encode(
        {
            "sub": str(user.id),
            "name": user.name,
            "email": user.email,
            "role": user.role,
            "type": _TOKEN_TYPE,
            "iss": _ISSUER,
            "iat": issued_at,
            "exp": issued_at + timedelta(seconds=expires_in),
        },
        settings.jwt_secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )
    return token, expires_in


def decode_access_token(token: str, settings: Settings) -> AuthenticatedUser:
    """Valida assinatura, expiracao e claims obrigatorias do token de acesso."""

    try:
        claims = jwt.decode(
            token,
            settings.jwt_secret_key.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
            issuer=_ISSUER,
            options={"require": ["sub", "name", "email", "role", "type", "iss", "iat", "exp"]},
        )
        if claims["type"] != _TOKEN_TYPE:
            raise InvalidAccessTokenError("Tipo de token invalido")
        return AuthenticatedUser(
            id=UUID(claims["sub"]),
            name=str(claims["name"]),
            email=str(claims["email"]),
            role=str(claims["role"]),
        )
    except (jwt.PyJWTError, KeyError, TypeError, ValueError) as exc:
        if isinstance(exc, InvalidAccessTokenError):
            raise
        raise InvalidAccessTokenError("Token de acesso invalido ou expirado") from exc
