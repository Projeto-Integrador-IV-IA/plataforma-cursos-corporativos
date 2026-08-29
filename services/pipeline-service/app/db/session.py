"""Engine e sessao do banco.

Contrato desta camada:
    - engine unico criado a partir de ``DATABASE_URL`` (RNF11);
    - ``get_session()`` como dependencia do FastAPI, com commit no sucesso e
      rollback na excecao;
    - pool dimensionado para o alvo de latencia do CRM (RNF07: <= 500 ms).

Nenhum outro microsservico acessa este banco - o acesso e exclusivo do
pipeline-service e se da por API (RNF01, RNF13).

O engine e criado sob demanda, permitindo importar a aplicacao sem abrir conexao.
"""

from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

from app.core.config import get_settings


@lru_cache
def get_engine() -> Engine:
    return create_engine(get_settings().database_url, pool_pre_ping=True)


def get_session() -> Generator[Session, None, None]:
    with Session(get_engine(), autoflush=False, expire_on_commit=False) as session:
        yield session
