"""Agregador das rotas da API v1 do pipeline-service.

O prefixo de versao (/api/v1) e obrigatorio: contratos de API sao
versionados e documentados entre os servicos (RNF02). Uma mudanca incompativel
abre a v2 em vez de alterar a v1 em uso.

TODO(scaffolding): montar o APIRouter e incluir os routers de routes/.
"""

from fastapi import APIRouter

from app.api.v1.routes.clients import router as clients_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(clients_router)
