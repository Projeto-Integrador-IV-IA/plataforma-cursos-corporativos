"""Rotas de negocio encaminhadas para os microsservicos internos."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from app.auth.dependencies import CurrentUser
from app.core.config import Settings, get_settings
from app.proxy.forwarder import forward_request
from app.proxy.routes_map import service_for_resource

router = APIRouter(tags=["proxy"])


def make_proxy_endpoint(resource: str):
    async def proxy_resource(
        request: Request,
        user: CurrentUser,
        settings: Annotated[Settings, Depends(get_settings)],
    ) -> Response:
        base_url = service_for_resource(resource, settings)
        if base_url is None:
            raise HTTPException(status_code=404, detail="Recurso nao encontrado")
        prefix = f"/api/v1/{resource}"
        path = request.url.path.removeprefix(prefix).lstrip("/")
        upstream_path = prefix if not path else f"{prefix}/{path}"
        return await forward_request(request, user, base_url, upstream_path)

    return proxy_resource


_RESOURCES = (
    "clients",
    "demands",
    "pipeline",
    "artifacts",
    "raw-inputs",
    "ingestion",
    "structuring",
)
_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
for _resource in _RESOURCES:
    _endpoint = make_proxy_endpoint(_resource)
    # Fora do schema (RNF02): o contrato publico do gateway cobre so
    # autenticacao; o contrato de cada recurso proxied e o do microsservico
    # de destino, ja publicado no respectivo arquivo em packages/contracts.
    router.add_api_route(
        f"/{_resource}", _endpoint, methods=_METHODS, include_in_schema=False
    )
    router.add_api_route(
        f"/{_resource}/{{path:path}}",
        _endpoint,
        methods=_METHODS,
        include_in_schema=False,
    )
