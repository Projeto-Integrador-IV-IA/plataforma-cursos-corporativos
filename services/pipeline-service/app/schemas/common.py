"""Schemas compartilhados pelos contratos HTTP do pipeline-service."""

from pydantic import BaseModel, Field


class PaginatedResponse[ItemT](BaseModel):
    """Envelope reutilizavel para listagens paginadas (RF03)."""

    items: list[ItemT]
    total: int = Field(ge=0, description="Total de registros que atendem aos filtros.")
    page: int = Field(ge=1, description="Pagina atual, calculada a partir de offset e limit.")
    size: int = Field(ge=1, description="Limite de registros solicitado por pagina.")
