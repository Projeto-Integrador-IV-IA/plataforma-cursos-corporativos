"""Endpoints de saude do ingestion-service.

Rotas:
    GET /health   - liveness: o processo HTTP esta de pe. Usado pelo healthcheck
                    do Docker Compose.
    GET /ready    - readiness: servicos a jusante (pipeline e ai-structuring).
                    Ainda nao implementado.

Nao exigem autenticacao e nao devem revelar detalhes internos de
infraestrutura (RNF10).

TODO(RNF01): implementar ``GET /ready`` quando as dependencias existirem.
"""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    """Confirma que o processo HTTP esta apto a responder."""

    return {"status": "ok", "service": "ingestion-service"}
