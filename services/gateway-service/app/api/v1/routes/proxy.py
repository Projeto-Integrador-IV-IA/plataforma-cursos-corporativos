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
    _slug = _resource.replace("-", "_")
    for _suffix, _suffix_slug in (("", ""), ("/{path:path}", "_path")):
        for _method in _METHODS:
            # Uma rota por metodo: registrar todos os metodos numa unica
            # chamada faz o FastAPI gerar o mesmo operation_id para todos
            # eles, escolhido de forma nao deterministica (route.methods e
            # um set) a cada geracao do schema - o que quebra o contrato
            # versionado (RNF02) de forma intermitente.
            router.add_api_route(
                f"/{_resource}{_suffix}",
                _endpoint,
                methods=[_method],
                operation_id=f"proxy_resource_api_v1_{_slug}{_suffix_slug}_{_method.lower()}",
            )
