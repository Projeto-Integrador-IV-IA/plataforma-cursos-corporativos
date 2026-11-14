"""Cobertura da matriz de autorizacao do gateway."""

from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.auth.dependencies import require_permission
from app.auth.jwt import AuthenticatedUser
from app.services.auth_service import Permission, Role, role_has_permission

MATRIX_EXPECTED = {
    Role.OPERADOR: {
        Permission.READ: True,
        Permission.CREATE: True,
        Permission.UPDATE: True,
        Permission.REVIEW: False,
        Permission.APPROVE: False,
        Permission.MANAGE_USERS: False,
    },
    Role.REVISOR: {
        Permission.READ: True,
        Permission.CREATE: False,
        Permission.UPDATE: False,
        Permission.REVIEW: True,
        Permission.APPROVE: True,
        Permission.MANAGE_USERS: False,
    },
    Role.ADMINISTRADOR: {permission: True for permission in Permission},
}


@pytest.mark.parametrize("role, permissions", MATRIX_EXPECTED.items())
def test_permission_matrix(role: Role, permissions: dict[Permission, bool]) -> None:
    for permission, expected in permissions.items():
        assert role_has_permission(role, permission) is expected


def test_unknown_role_uses_least_privilege() -> None:
    assert role_has_permission("perfil-desconhecido", Permission.READ)
    assert role_has_permission("perfil-desconhecido", Permission.CREATE)
    assert not role_has_permission("perfil-desconhecido", Permission.REVIEW)
    assert not role_has_permission("perfil-desconhecido", Permission.MANAGE_USERS)


def test_protected_dependency_returns_403_without_permission() -> None:
    user = AuthenticatedUser(
        id=uuid4(), name="Revisor", email="revisor@example.com", role=Role.REVISOR
    )

    with pytest.raises(HTTPException) as error:
        require_permission(Permission.CREATE)(user)

    assert error.value.status_code == 403
