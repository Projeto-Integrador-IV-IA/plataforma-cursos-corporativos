"""Erros tipados e envelope HTTP comum do ingestion-service."""

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class PlatformError(Exception):
    def __init__(
        self,
        *,
        status_code: int,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details


class UpstreamError(PlatformError):
    """Falha explicita do pipeline-service ou da comunicacao com ele."""


def _error_content(request: Request, exc: PlatformError) -> dict[str, Any]:
    error: dict[str, Any] = {"code": exc.code, "message": exc.message}
    if exc.details is not None:
        error["details"] = exc.details
    if request_id := request.headers.get("X-Request-ID"):
        error["request_id"] = request_id
    return {"error": error}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(PlatformError)
    async def handle_platform_error(request: Request, exc: PlatformError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content=_error_content(request, exc))

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        error = PlatformError(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            code="VALIDATION_ERROR",
            message="Os dados informados sao invalidos.",
            details={
                "issues": [
                    {
                        "location": list(issue["loc"]),
                        "message": issue["msg"],
                        "type": issue["type"],
                    }
                    for issue in exc.errors()
                ]
            },
        )
        return JSONResponse(status_code=error.status_code, content=_error_content(request, error))
