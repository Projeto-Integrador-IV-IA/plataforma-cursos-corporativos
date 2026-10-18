"""Excecoes de dominio e traducao para respostas HTTP.

Erros previsiveis viram excecoes tipadas aqui e sao traduzidos em um corpo de
erro unico para toda a plataforma, de modo que o frontend trate qualquer
servico da mesma forma (RNF02).

Formato de erro acordado entre os servicos:
    {"error": {"code": "DEMAND_NOT_FOUND", "message": "...", "details": {...}}}

Hierarquia prevista:
    PlatformError                 base de todas
    ├── NotFoundError             recurso inexistente            -> 404
    ├── ValidationError           entrada invalida               -> 422
    ├── ConflictError             transicao de etapa invalida    -> 409
    ├── UnauthorizedError         sem autenticacao (RF26)        -> 401
    └── UpstreamError             falha de servico dependente    -> 502/504
        └── LLMUnavailableError   timeout/erro do LLM (RNF05)    -> 503

"""

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class PlatformError(Exception):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    def __init__(self, *, code: str, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details


class UnauthorizedError(PlatformError):
    status_code = status.HTTP_401_UNAUTHORIZED

    def __init__(self, *, code: str = "UNAUTHORIZED", message: str = "Sessao ausente ou invalida."):
        super().__init__(code=code, message=message)


class UpstreamError(PlatformError):
    status_code = status.HTTP_502_BAD_GATEWAY


def _content(request: Request, exc: PlatformError) -> dict[str, Any]:
    error: dict[str, Any] = {"code": exc.code, "message": exc.message}
    if exc.details is not None:
        error["details"] = exc.details
    if request_id := request.headers.get("X-Request-ID"):
        error["request_id"] = request_id
    return {"error": error}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(PlatformError)
    async def handle_platform_error(request: Request, exc: PlatformError) -> JSONResponse:
        headers = {"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else None
        return JSONResponse(
            status_code=exc.status_code, content=_content(request, exc), headers=headers
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        issues = [
            {"location": list(error["loc"]), "message": error["msg"], "type": error["type"]}
            for error in exc.errors()
        ]
        platform_error = PlatformError(
            code="VALIDATION_ERROR",
            message="Os dados informados sao invalidos.",
            details={"issues": issues},
        )
        platform_error.status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
        return JSONResponse(
            status_code=platform_error.status_code,
            content=_content(request, platform_error),
        )
