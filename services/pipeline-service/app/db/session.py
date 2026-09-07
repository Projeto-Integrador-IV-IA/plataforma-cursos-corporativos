"""Engine e ciclo transacional das sessoes do pipeline-service."""

from collections.abc import Iterator
from functools import lru_cache

import sqlalchemy as sa
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


@lru_cache
def get_engine() -> Engine:
    """Cria um unico engine, lendo a credencial apenas do ambiente (RNF11)."""

    database_url = get_settings().database_url.get_secret_value()
    url = make_url(database_url)
    options: dict[str, object] = {"pool_pre_ping": True}

    if url.get_backend_name() != "sqlite":
        options.update(pool_size=5, max_overflow=10, pool_timeout=30)

    return sa.create_engine(url, **options)


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    """Retorna a fabrica de sessoes vinculada ao engine do processo."""

    return sessionmaker(
        bind=get_engine(),
        class_=Session,
        autoflush=False,
        expire_on_commit=False,
    )


def get_session() -> Iterator[Session]:
    """Fornece uma sessao por requisicao, com commit ou rollback atomico."""

    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
