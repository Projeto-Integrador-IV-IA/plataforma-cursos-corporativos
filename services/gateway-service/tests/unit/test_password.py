"""Testes de hash de senha."""

import pytest

from app.auth.password import hash_password, verify_password

# Senha usada para gerar o hash de compatibilidade abaixo. Vale so nos testes.
SAMPLE_PASSWORD = "senha-de-teste-nao-versionada"

# Hash emitido pela implementacao anterior (passlib 1.7.4 sobre bcrypt). Serve
# de prova de que a troca para bcrypt direto nao invalida hash ja gravado.
LEGACY_PASSLIB_HASH = "$2b$12$heIORp2ABS9dP2B1M.hxTeb768cxVdQy7eUOAdLNbdkGWdI/VbfSW"


def test_password_is_hashed_and_can_be_verified() -> None:
    password = SAMPLE_PASSWORD

    password_hash = hash_password(password)

    assert password_hash != password
    assert password not in password_hash
    assert hash_password(password) != password_hash
    assert verify_password(password, password_hash)
    assert not verify_password("senha-incorreta", password_hash)


def test_hash_uses_bcrypt_modular_crypt_format() -> None:
    assert hash_password(SAMPLE_PASSWORD).startswith("$2b$12$")


def test_empty_password_is_rejected() -> None:
    with pytest.raises(ValueError):
        hash_password("")


def test_password_over_bcrypt_limit_is_rejected() -> None:
    with pytest.raises(ValueError):
        hash_password("a" * 73)

    assert not verify_password("a" * 73, hash_password(SAMPLE_PASSWORD))


def test_malformed_hash_is_rejected_without_error() -> None:
    assert not verify_password("qualquer-senha", "nao-e-um-hash")
    assert not verify_password("qualquer-senha", "$2b$12$curto")
    assert not verify_password("qualquer-senha", "")


def test_hash_from_previous_implementation_still_verifies() -> None:
    """Hash `$2b$` gerado pelo passlib continua verificavel (RNF11)."""

    assert verify_password(SAMPLE_PASSWORD, LEGACY_PASSLIB_HASH)
    assert not verify_password("senha-incorreta", LEGACY_PASSLIB_HASH)
