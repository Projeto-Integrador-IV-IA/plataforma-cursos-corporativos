"""Hash e verificacao segura de senhas (RNF10 e RNF11)."""

from passlib.context import CryptContext
from passlib.exc import UnknownHashError

_BCRYPT_MAX_BYTES = 72
_password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Gera um hash bcrypt com salt; a senha original nunca e persistida."""

    if not password:
        raise ValueError("A senha nao pode ser vazia")
    if len(password.encode("utf-8")) > _BCRYPT_MAX_BYTES:
        raise ValueError("A senha excede o limite seguro do bcrypt")
    return _password_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Compara uma senha com um hash valido sem expor detalhes ao chamador."""

    if not password or not password_hash:
        return False
    if len(password.encode("utf-8")) > _BCRYPT_MAX_BYTES:
        return False
    try:
        return _password_context.verify(password, password_hash)
    except (UnknownHashError, ValueError):
        return False
