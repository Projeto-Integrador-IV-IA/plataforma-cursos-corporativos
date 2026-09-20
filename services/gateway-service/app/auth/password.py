"""Hash e verificacao segura de senhas (RNF10 e RNF11).

Usa a biblioteca `bcrypt` diretamente, sem intermediario. O formato gravado e o
modular crypt padrao (`$2b$...`), o mesmo emitido pela implementacao anterior
baseada em passlib, entao hashes ja existentes continuam verificaveis.
"""

import bcrypt

# O bcrypt so considera os primeiros 72 bytes da senha. Em vez de truncar em
# silencio - o que faria duas senhas distintas colidirem - recusamos a entrada.
_BCRYPT_MAX_BYTES = 72

# Custo do bcrypt: 2**12 rounds, o padrao atual da biblioteca.
_BCRYPT_ROUNDS = 12


def hash_password(password: str) -> str:
    """Gera um hash bcrypt com salt; a senha original nunca e persistida."""

    if not password:
        raise ValueError("A senha nao pode ser vazia")
    password_bytes = password.encode("utf-8")
    if len(password_bytes) > _BCRYPT_MAX_BYTES:
        raise ValueError("A senha excede o limite seguro do bcrypt")
    salt = bcrypt.gensalt(rounds=_BCRYPT_ROUNDS)
    return bcrypt.hashpw(password_bytes, salt).decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    """Compara uma senha com um hash valido sem expor detalhes ao chamador."""

    if not password or not password_hash:
        return False
    password_bytes = password.encode("utf-8")
    if len(password_bytes) > _BCRYPT_MAX_BYTES:
        return False
    try:
        return bcrypt.checkpw(password_bytes, password_hash.encode("utf-8"))
    except (TypeError, ValueError, UnicodeEncodeError):
        # Hash malformado ou fora do formato bcrypt e falha de verificacao,
        # nunca um erro propagado para quem autentica.
        return False
