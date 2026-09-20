"""Captacao que persiste o bruto antes de qualquer etapa posterior (RF09)."""

from uuid import UUID

from app.clients.pipeline_client import PipelineClient
from app.domain.raw_demand import PersistedRawDemand, RawDemand


class IngestionService:
    def __init__(self, pipeline_client: PipelineClient) -> None:
        self.pipeline_client = pipeline_client

    def capture(
        self,
        raw_demand: RawDemand,
        *,
        author_id: UUID,
        request_id: str | None = None,
    ) -> PersistedRawDemand:
        """Encerra a captacao apos o commit remoto, sem normalizar o original."""

        return self.pipeline_client.persist_raw_demand(
            raw_demand,
            author_id=author_id,
            request_id=request_id,
        )
