"""Correlacao de log entre servicos pelo cabecalho X-Request-ID.

Os demais servicos ja propagam e logam ``X-Request-ID`` quando ele chega
(``app/core/logging.py`` de cada um), mas nenhum o cria: o navegador nunca
manda esse cabecalho por conta propria, e sem alguem originando o primeiro
valor a cadeia de correlacao nunca comeca. O gateway e a borda - e aqui, e so
aqui, que faz sentido gerar um identificador quando a requisicao chega sem um.
"""

from collections.abc import Awaitable, Callable
from uuid import uuid4

from fastapi import FastAPI, Request, Response

REQUEST_ID_HEADER = b"x-request-id"


def register_correlation_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def _correlate(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        existing = request.headers.get("X-Request-ID")
        request_id = existing or str(uuid4())
        if existing is None:
            # Injeta no scope, nao so numa variavel local: e dali que
            # `request.headers` e o encaminhamento ao servico interno
            # (`forward_request`) leem, e os dois precisam ver o mesmo valor
            # que a resposta devolve.
            request.scope["headers"].append((REQUEST_ID_HEADER, request_id.encode()))

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
