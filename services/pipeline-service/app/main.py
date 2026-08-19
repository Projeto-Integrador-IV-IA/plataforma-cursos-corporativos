"""Ponto de entrada do pipeline-service.

CRM: clientes, demandas, etapas, historico e artefatos versionados.

Responsabilidades deste modulo:
    - criar a instancia da aplicacao FastAPI com titulo, versao e metadados de OpenAPI;
    - registrar o roteador da API v1 (RNF02: contratos versionados);
    - registrar middlewares transversais (CORS, correlacao de requisicao, log de acesso);
    - registrar os handlers de excecao definidos em app.core.exceptions;
    - expor os endpoints de saude usados pelo Docker Compose e pela CI.

TODO(scaffolding): implementar a fabrica create_app() e expor app.
    Ate la este servico nao sobe - ver README na raiz do repositorio.
"""

# TODO: from fastapi import FastAPI
# TODO: def create_app() -> FastAPI: ...
# TODO: app = create_app()
