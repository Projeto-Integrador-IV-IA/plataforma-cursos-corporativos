"""Endpoint de liveness do ai-structuring-service."""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    """Confirma que o processo HTTP esta apto a responder."""

    return {"status": "ok", "service": "ai-structuring-service"}
