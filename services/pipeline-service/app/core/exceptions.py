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
    ├── UnauthorizedError         sem autenticacao (RF16)        -> 401
    ├── ForbiddenError            sem permissao (RNF10)          -> 403
    └── UpstreamError             falha de servico dependente    -> 502/504
        └── LLMUnavailableError   timeout/erro do LLM (RNF05)    -> 503

Implementa a hierarquia basica e os handlers compartilhados pelo servico.
"""

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class PlatformError(Exception):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    def __init__(
        self,
        *,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details


class NotFoundError(PlatformError):
    status_code = status.HTTP_404_NOT_FOUND


class ConflictError(PlatformError):
    status_code = status.HTTP_409_CONFLICT


class ServiceUnavailableError(PlatformError):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE


def _error_content(
    *,
    code: str,
    message: str,
    request: Request,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    error: dict[str, Any] = {"code": code, "message": message}
    if details is not None:
        error["details"] = details
    if request_id := request.headers.get("X-Request-ID"):
        error["request_id"] = request_id
    return {"error": error}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(PlatformError)
    async def handle_platform_error(request: Request, exc: PlatformError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_content(
                code=exc.code,
                message=exc.message,
                details=exc.details,
                request=request,
            ),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        issues = [
            {"location": list(error["loc"]), "message": error["msg"], "type": error["type"]}
            for error in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content=_error_content(
                code="VALIDATION_ERROR",
                message="Os dados informados são inválidos.",
                details={"issues": issues},
                request=request,
            ),
        )
