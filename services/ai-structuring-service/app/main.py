"""Ponto de entrada do ai-structuring-service.

Estruturacao do curso por LLM com schema de saida fixo.

Responsabilidades deste modulo:
    - criar a instancia da aplicacao FastAPI com titulo, versao e metadados de OpenAPI;
    - registrar o roteador da API v1 (RNF02: contratos versionados);
    - registrar middlewares transversais (CORS, correlacao de requisicao, log de acesso);
    - registrar os handlers de excecao definidos em app.core.exceptions;
    - expor os endpoints de saude usados pelo Docker Compose e pela CI.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.api.v1.routes.health import router as health_router
from app.core.exceptions import PlatformError

#: Header que carrega a correlacao da requisicao entre os servicos (RNF09).
REQUEST_ID_HEADER = "x-request-id"


async def handle_platform_error(request: Request, exc: PlatformError) -> JSONResponse:
    """Traduz erro previsivel de dominio no corpo unico de erro da plataforma.

    Sem este handler, uma falha do provedor de LLM viraria 500 generico e o
    operador nao saberia se foi timeout, indisponibilidade ou limite de uso -
    nem se vale reprocessar a demanda (RNF02, RNF05).

    O status vem da propria excecao e a correlacao, do header ``X-Request-ID``,
    para que o erro visto na tela seja localizavel no log (RNF09).
    """

    return JSONResponse(
        status_code=exc.http_status,
        content=exc.to_error_payload(request.headers.get(REQUEST_ID_HEADER)),
    )


def register_exception_handlers(application: FastAPI) -> None:
    """Registra a traducao das excecoes de dominio em resposta HTTP (RNF02)."""

    application.add_exception_handler(
        PlatformError,
        handle_platform_error,  # type: ignore[arg-type]
    )


def create_app() -> FastAPI:
    """Cria a aplicacao e registra as fronteiras HTTP publicas."""

    application = FastAPI(title="ai-structuring-service", version="0.1.0")
    application.include_router(health_router)
    application.include_router(api_router)
    register_exception_handlers(application)
    return application


app = create_app()
