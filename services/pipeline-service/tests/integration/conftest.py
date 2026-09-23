"""Fixtures compartilhadas pelos testes de integracao do pipeline-service.

``engine``, ``api`` e ``company`` vivem aqui porque mais de um arquivo de aceite
precisa do mesmo banco migrado com chaves estrangeiras ativas - duplicar a
montagem em cada arquivo faria as suites divergirem em silencio.
"""

from collections.abc import Iterator
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.session import get_session
from app.main import create_app
from app.models import Client

from ._schema import migrated_connection


@pytest.fixture
def database() -> Iterator[Connection]:
    """Conexao sobre o schema criado pela migration inicial."""

    yield from migrated_connection()


@pytest.fixture
def engine(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Engine]:
    """Aplica a cadeia Alembic em um banco temporario, sem acessar dados reais."""

    from app.core.config import get_settings

    database_url = f"sqlite+pysqlite:///{(tmp_path / 'pipeline.sqlite3').as_posix()}"
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    monkeypatch.setenv("PIPELINE_PORT", "8001")
    monkeypatch.setenv("DATABASE_URL", database_url)
    get_settings.cache_clear()
    config = Config("alembic.ini")
    command.upgrade(config, "head")
    engine = sa.create_engine(
        database_url, connect_args={"check_same_thread": False}, poolclass=StaticPool
    )

    @sa.event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection: Any, _connection_record: Any) -> None:
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    try:
        yield engine
    finally:
        engine.dispose()
        command.downgrade(config, "base")
        get_settings.cache_clear()


@pytest.fixture
def api(engine: Engine) -> Iterator[TestClient]:
    application = create_app()

    def session_override() -> Iterator[Session]:
        with Session(engine, expire_on_commit=False) as session:
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise

    application.dependency_overrides[get_session] = session_override
    with TestClient(application) as client:
        yield client


@pytest.fixture
def company(engine: Engine) -> UUID:
    with Session(engine) as session:
        client = Client(name="Empresa de teste")
        session.add(client)
        session.commit()
        return client.id
