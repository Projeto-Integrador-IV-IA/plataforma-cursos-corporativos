"""Endpoints de saude do pipeline-service.

Rotas previstas:
    GET /health   - o processo esta de pe (liveness).
    GET /ready    - as dependencias respondem (readiness): banco, servicos
                    a jusante e provedor de LLM, conforme o caso.

Usados pelo healthcheck do Docker Compose e pela CI. Nao exigem autenticacao e
nao devem revelar detalhes internos de infraestrutura (RNF10).

TODO(scaffolding): implementar as rotas.
"""

# TODO: router = APIRouter(tags=["health"])
