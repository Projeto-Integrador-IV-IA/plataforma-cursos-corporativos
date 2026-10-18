"""Ponto de entrada do pipeline-service.

CRM: clientes, demandas, etapas, historico e artefatos versionados.

Responsabilidades deste modulo:
    - criar a instancia da aplicacao FastAPI com titulo, versao e metadados de OpenAPI;
    - registrar o roteador da API v1 (RNF02: contratos versionados);
    - registrar middlewares transversais (CORS, correlacao de requisicao, log de acesso);
    - registrar os handlers de excecao definidos em app.core.exceptions;
    - expor os endpoints de saude usados pelo Docker Compose e pela CI.
"""

from fastapi import FastAPI

from app.api.v1.router import api_router
from app.api.v1.routes.health import router as health_router
from app.api.v1.routes.internal_auth import router as internal_auth_router
from app.core.exceptions import register_exception_handlers


def create_app() -> FastAPI:
    """Cria a aplicacao e registra as fronteiras HTTP publicas."""

    application = FastAPI(title="pipeline-service", version="0.1.0")
    register_exception_handlers(application)
    application.include_router(health_router)
    # Fronteira exclusiva entre servicos; fica fora do agregador publico para
    # nao sugerir que esta rota de credenciais faz parte do BFF.
    application.include_router(internal_auth_router)
    application.include_router(api_router)
    return application


app = create_app()
