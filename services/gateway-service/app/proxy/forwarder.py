"""Encaminhamento autenticado para os microsservicos internos."""

import httpx
from fastapi import HTTPException, Request, Response

from app.auth.dependencies import CurrentUser


async def forward_request(
    request: Request, user: CurrentUser, base_url: str, upstream_path: str
) -> Response:
    """Preserva metodo, query e corpo, injetando a identidade autenticada."""
    headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in {"host", "authorization", "content-length", "connection"}
    }
    headers["X-User-ID"] = str(user.id)
    try:
        async with httpx.AsyncClient(base_url=base_url.rstrip("/"), timeout=15.0) as client:
            upstream = await client.request(
                request.method,
                f"/{upstream_path.lstrip('/')}",
                params=request.query_params,
                content=await request.body(),
                headers=headers,
            )
    except httpx.TimeoutException as exc:
        raise HTTPException(
            status_code=504, detail="Servico interno expirou o tempo de resposta"
        ) from exc
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail="Servico interno indisponivel") from exc

    excluded = {"content-length", "transfer-encoding", "connection", "content-encoding"}
    response_headers = {k: v for k, v in upstream.headers.items() if k.lower() not in excluded}
    return Response(
        content=upstream.content, status_code=upstream.status_code, headers=response_headers
    )
