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
        upstream_path = f"/api/v1/{resource}"
        return await forward_request(request, user, base_url, upstream_path)

    return proxy_resource


def make_proxy_endpoint_with_path(resource: str):
    # ``path`` entra na assinatura so para o OpenAPI documentar o parametro de
    # caminho declarado na rota (``{path:path}``) - sem ele, o FastAPI nao sabe
    # que a URL tem um segmento variavel e o contrato gerado fica invalido.
    async def proxy_resource_with_path(
        path: str,
        request: Request,
        user: CurrentUser,
        settings: Annotated[Settings, Depends(get_settings)],
    ) -> Response:
        base_url = service_for_resource(resource, settings)
        if base_url is None:
            raise HTTPException(status_code=404, detail="Recurso nao encontrado")
        upstream_path = f"/api/v1/{resource}/{path}"
        return await forward_request(request, user, base_url, upstream_path)

    return proxy_resource_with_path


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
    _endpoint_with_path = make_proxy_endpoint_with_path(_resource)
    _slug = _resource.replace("-", "_")
    for _method in _METHODS:
        router.add_api_route(
            f"/{_resource}",
            _endpoint,
            methods=[_method],
            operation_id=f"proxy_{_slug}_{_method.lower()}",
        )
        router.add_api_route(
            f"/{_resource}/{{path:path}}",
            _endpoint_with_path,
            methods=[_method],
            operation_id=f"proxy_{_slug}_path_{_method.lower()}",
        )
