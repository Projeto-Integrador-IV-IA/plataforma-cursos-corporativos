"""Whitelist de recursos de negocio encaminhados pelo gateway."""

from app.core.config import Settings


def service_for_resource(resource: str, settings: Settings) -> str | None:
    """Resolve o recurso conhecido para a URL interna do microsservico dono."""
    routes = {
        "clients": settings.pipeline_service_url,
        "demands": settings.pipeline_service_url,
        "pipeline": settings.pipeline_service_url,
        "artifacts": settings.pipeline_service_url,
        "raw-inputs": settings.pipeline_service_url,
        "ingestion": settings.ingestion_service_url,
        "structuring": settings.ai_structuring_service_url,
    }
    return routes.get(resource)
