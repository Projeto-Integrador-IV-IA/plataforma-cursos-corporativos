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

# TODO: def get_session(): ...
