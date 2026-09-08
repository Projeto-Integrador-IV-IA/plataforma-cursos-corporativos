"""Agregador das rotas da API v1 do ai-structuring-service.

O prefixo de versao (/api/v1) e obrigatorio: contratos de API sao
versionados e documentados entre os servicos (RNF02). Uma mudanca incompativel
abre a v2 em vez de alterar a v1 em uso.

"""

from fastapi import APIRouter

api_router = APIRouter(prefix="/api/v1")
