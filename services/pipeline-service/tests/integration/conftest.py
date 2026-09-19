"""Fixtures compartilhadas pelos testes de integracao do pipeline-service."""

from collections.abc import Iterator

import pytest
from sqlalchemy.engine import Connection

from ._schema import migrated_connection


@pytest.fixture
def database() -> Iterator[Connection]:
    """Conexao sobre o schema criado pela migration inicial."""

    yield from migrated_connection()
