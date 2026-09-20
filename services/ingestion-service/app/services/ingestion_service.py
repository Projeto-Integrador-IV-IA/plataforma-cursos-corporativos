"""Captacao que persiste o bruto antes de qualquer etapa posterior (RF09)."""

from uuid import UUID

from app.clients.pipeline_client import PipelineClient
from app.domain.raw_demand import PersistedRawDemand, RawDemand
from app.normalizers.text_normalizer import normalize_text


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
        """Persiste o original, sanitiza uma copia e grava o resultado separadamente."""

        persisted = self.pipeline_client.persist_raw_demand(
            raw_demand,
            author_id=author_id,
            request_id=request_id,
        )
        normalized_content = normalize_text(raw_demand.text, raw_demand.source_type)
        self.pipeline_client.persist_normalization(
            persisted.raw_input_id,
            normalized_content,
            request_id=request_id,
        )
        return persisted
