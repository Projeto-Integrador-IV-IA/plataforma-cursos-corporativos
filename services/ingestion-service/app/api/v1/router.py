"""Agregador das rotas da API v1 do ingestion-service.

O prefixo de versao (/api/v1) e obrigatorio: contratos de API sao
versionados e documentados entre os servicos (RNF02). Uma mudanca incompativel
abre a v2 em vez de alterar a v1 em uso.
"""

from fastapi import APIRouter

from app.api.v1.routes.ingestion import router as ingestion_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(ingestion_router)
