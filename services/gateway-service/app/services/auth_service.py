"""Caso de uso: autenticacao do operador (RF26 e RNF18 consolidados).

Fluxo de login: buscar usuario ativo pelo e-mail, verificar a senha contra o
hash, emitir o token. Falha em qualquer passo produz a mesma resposta generica.

O cadastro de usuarios mora no pipeline-service; este servico o consulta por
API (RNF01).

"""

from enum import StrEnum
from uuid import UUID

import httpx
from pydantic import BaseModel, EmailStr

from app.auth.jwt import AuthenticatedUser, create_access_token
from app.auth.password import verify_password
from app.core.config import Settings
from app.core.exceptions import UnauthorizedError, UpstreamError
from app.schemas.auth import LoginRequest, OperatorInfo, TokenResponse

# Verificacao dummy reduz a diferenca de tempo entre e-mail inexistente e senha
# incorreta. E apenas um hash bcrypt de teste, nao uma credencial utilizavel.
_DUMMY_HASH = "$2b$12$heIORp2ABS9dP2B1M.hxTeb768cxVdQy7eUOAdLNbdkGWdI/VbfSW"


class Role(StrEnum):
    """Perfis reconhecidos pelo gateway.

    Valores desconhecidos nunca recebem privilegios por acidente: a camada de
    autenticacao os reduz a ``OPERADOR`` antes de criar o token.
    """

    OPERADOR = "OPERADOR"
    REVISOR = "REVISOR"
    ADMINISTRADOR = "ADMINISTRADOR"


class Permission(StrEnum):
    """Operacoes que podem ser protegidas por uma rota do gateway."""

    READ = "read"
    CREATE = "create"
    UPDATE = "update"
    REVIEW = "review"
    APPROVE = "approve"
    MANAGE_USERS = "manage_users"


ALL_PERMISSIONS = frozenset(Permission)

# Matriz central de autorizacao. A ausencia de uma permissao significa
# negacao; nao existe fallback permissivo.
PERMISSION_MATRIX: dict[Role, frozenset[Permission]] = {
    Role.OPERADOR: frozenset({Permission.READ, Permission.CREATE, Permission.UPDATE}),
    Role.REVISOR: frozenset({Permission.READ, Permission.REVIEW, Permission.APPROVE}),
    Role.ADMINISTRADOR: ALL_PERMISSIONS,
}


def normalize_role(role: str | Role) -> Role:
    """Converte o perfil persistido para um perfil conhecido e seguro."""

    try:
        return Role(str(role).strip().upper())
    except ValueError:
        return Role.OPERADOR


def role_has_permission(role: str | Role, permission: str | Permission) -> bool:
    """Retorna se o perfil possui a operacao, aplicando menor privilegio."""

    normalized_role = normalize_role(role)
    try:
        normalized_permission = Permission(str(permission).strip().lower())
    except ValueError:
        return False
    return normalized_permission in PERMISSION_MATRIX[normalized_role]


class UserCredentials(BaseModel):
    id: UUID
    name: str
    email: EmailStr
    password_hash: str
    role: str
    active: bool


class AuthService:
    def __init__(self, http_client: httpx.Client, settings: Settings) -> None:
        self.http_client = http_client
        self.settings = settings

    def login(self, data: LoginRequest) -> TokenResponse:
        """Valida credenciais sem distinguir usuario inexistente de senha errada."""

        user = self._find_user(data.email)
        password_hash = user.password_hash if user is not None else _DUMMY_HASH
        password_ok = verify_password(data.password, password_hash)
        if user is None or not user.active or not password_ok:
            raise UnauthorizedError(
                code="INVALID_CREDENTIALS", message="E-mail ou senha incorretos."
            )

        authenticated = AuthenticatedUser(
            id=user.id,
            name=user.name,
            email=str(user.email),
            role=normalize_role(user.role).value,
        )
        token, expires_in = create_access_token(authenticated, self.settings)
        return TokenResponse(
            access_token=token,
            expires_in=expires_in,
            operator=OperatorInfo(
                id=authenticated.id,
                name=authenticated.name,
                email=authenticated.email,
                role=authenticated.role,
            ),
        )

    def _find_user(self, email: str) -> UserCredentials | None:
        try:
            response = self.http_client.get(
                "/api/v1/internal/auth/users/by-email",
                params={"email": email.strip().casefold()},
                headers={
                    "X-Service-Key": self.settings.auth_service_key.get_secret_value(),
                },
            )
        except httpx.RequestError as exc:
            raise UpstreamError(
                code="AUTH_USER_STORE_UNAVAILABLE",
                message="Nao foi possivel consultar os usuarios no momento.",
            ) from exc

        if response.status_code == 404:
            return None
        if response.status_code != 200:
            raise UpstreamError(
                code="AUTH_USER_STORE_UNAVAILABLE",
                message="O cadastro de usuarios devolveu uma resposta inesperada.",
                details={"status": response.status_code},
            )
        try:
            return UserCredentials.model_validate(response.json())
        except ValueError as exc:
            raise UpstreamError(
                code="AUTH_USER_STORE_INVALID_RESPONSE",
                message="O cadastro de usuarios devolveu dados invalidos.",
            ) from exc
