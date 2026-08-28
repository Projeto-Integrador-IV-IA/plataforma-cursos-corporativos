"""Engine e sessao do banco.

Contrato desta camada:
    - engine unico criado a partir de ``DATABASE_URL`` (RNF11);
    - ``get_session()`` como dependencia do FastAPI, com commit no sucesso e
      rollback na excecao;
    - pool dimensionado para o alvo de latencia do CRM (RNF07: <= 500 ms).

Nenhum outro microsservico acessa este banco - o acesso e exclusivo do
pipeline-service e se da por API (RNF01, RNF13).

TODO(scaffolding): implementar ``engine``, ``SessionLocal`` e ``get_session()``.
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

engine = create_engine(get_settings().database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_session() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
