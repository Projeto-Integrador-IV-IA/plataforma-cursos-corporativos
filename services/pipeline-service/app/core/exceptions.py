"""Excecoes tipadas e traducao para o envelope HTTP da plataforma (RNF02)."""

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


class ValidationError(PlatformError):
    """Entrada invalida que o Pydantic nao pega sozinho, como faixa de datas.

    Emite o mesmo ``details`` do handler de ``RequestValidationError`` para que
    o consumidor trate um formato so (RNF02) - ver ``issue_de_validacao``.
    """

    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT


class ConflictError(PlatformError):
    status_code = status.HTTP_409_CONFLICT


def issue_de_validacao(*, localizacao: list[str], mensagem: str, tipo: str) -> dict[str, Any]:
    """Monta uma entrada de ``details.issues`` no formato do handler global."""

    return {"location": localizacao, "message": mensagem, "type": tipo}


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
    """Registra uma unica traducao para erros de dominio e de entrada."""

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
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content=_error_content(
                code="VALIDATION_ERROR",
                message="Os dados informados sao invalidos.",
                details={"issues": issues},
                request=request,
            ),
        )
