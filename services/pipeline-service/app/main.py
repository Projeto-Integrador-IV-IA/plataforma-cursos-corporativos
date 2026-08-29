"""Ponto de entrada do pipeline-service.

CRM: clientes, demandas, etapas, historico e artefatos versionados.

Responsabilidades deste modulo:
    - criar a instancia da aplicacao FastAPI com titulo, versao e metadados de OpenAPI;
    - registrar o roteador da API v1 (RNF02: contratos versionados);
    - registrar middlewares transversais (CORS, correlacao de requisicao, log de acesso);
    - registrar os handlers de excecao definidos em app.core.exceptions;
    - expor os endpoints de saude usados pelo Docker Compose e pela CI.

Implementa a fabrica da aplicacao e registra rotas e handlers compartilhados.
"""

from fastapi import FastAPI

from app.api.v1.router import api_router
from app.api.v1.routes.health import router as health_router
from app.core.exceptions import register_exception_handlers


def create_app() -> FastAPI:
    application = FastAPI(title="pipeline-service", version="1.0.0")
    register_exception_handlers(application)
    application.include_router(health_router)
    application.include_router(api_router)
    return application


app = create_app()
