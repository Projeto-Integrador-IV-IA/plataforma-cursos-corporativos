"""Testes de hash de senha."""

import pytest

from app.auth.password import hash_password, verify_password


def test_password_is_hashed_and_can_be_verified() -> None:
    password = "senha-de-teste-nao-versionada"

    password_hash = hash_password(password)

    assert password_hash != password
    assert password not in password_hash
    assert hash_password(password) != password_hash
    assert verify_password(password, password_hash)
    assert not verify_password("senha-incorreta", password_hash)


def test_empty_password_is_rejected() -> None:
    with pytest.raises(ValueError):
        hash_password("")


def test_malformed_hash_is_rejected_without_error() -> None:
    assert not verify_password("qualquer-senha", "nao-e-um-hash")
