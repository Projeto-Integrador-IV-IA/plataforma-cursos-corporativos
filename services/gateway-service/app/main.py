"""Ponto de entrada do gateway-service.

Porta de entrada unica: autenticacao, roteamento e agregacao para o frontend.

Responsabilidades deste modulo:
    - criar a instancia da aplicacao FastAPI com titulo, versao e metadados de OpenAPI;
    - registrar o roteador da API v1 (RNF02: contratos versionados);
    - registrar middlewares transversais (CORS, correlacao de requisicao por
      X-Request-ID); log de acesso basico vem do proprio uvicorn;
    - registrar os handlers de excecao definidos em app.core.exceptions;
    - expor os endpoints de saude usados pelo Docker Compose e pela CI.
"""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.api.v1.routes.health import router as health_router
from app.core.correlation import register_correlation_middleware
from app.core.exceptions import register_exception_handlers

#: Mesmo padrao de `Settings.cors_allowed_origins` (app/core/config.py), mas lido
#: direto do ambiente: `create_app()` precisa funcionar sem nenhuma variavel
#: definida (e o que os testes fazem), e `Settings()` exige todas as outras
#: obrigatorias (chaves, URLs) so para ler esta.
_CORS_ALLOWED_ORIGINS_DEFAULT = "http://localhost:5173,http://localhost:5174"


def create_app() -> FastAPI:
    """Cria a aplicacao e registra as fronteiras HTTP publicas."""

    application = FastAPI(title="gateway-service", version="0.1.0")
    register_exception_handlers(application)
    register_correlation_middleware(application)
    origins = os.environ.get("CORS_ALLOWED_ORIGINS", _CORS_ALLOWED_ORIGINS_DEFAULT)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[origin.strip() for origin in origins.split(",") if origin.strip()],
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )
    application.include_router(health_router)
    application.include_router(api_router)
    return application


app = create_app()
