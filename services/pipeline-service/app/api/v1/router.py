"""Agregador das rotas da API v1 do pipeline-service.

O prefixo de versao (/api/v1) e obrigatorio: contratos de API sao
versionados e documentados entre os servicos (RNF02). Uma mudanca incompativel
abre a v2 em vez de alterar a v1 em uso.
"""

from fastapi import APIRouter

from app.api.v1.routes.demands import router as demands_router

# Ainda sem rotas de negocio: cada router de ``routes/`` entra aqui com
# ``api_router.include_router(...)`` a medida que seu contrato for implementado.
# O health fica fora do prefixo versionado porque e infraestrutura, nao contrato.
api_router = APIRouter(prefix="/api/v1")
api_router.include_router(demands_router)
