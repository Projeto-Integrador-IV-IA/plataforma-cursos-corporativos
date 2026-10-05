"""Ordem e separacao entre persistencia do original e da copia sanitizada."""

from datetime import UTC, datetime
from uuid import uuid4

from app.domain.raw_demand import PersistedRawDemand, RawDemand, SourceKind
from app.services.ingestion_service import IngestionService


class PipelineClientSpy:
    def __init__(self, persisted: PersistedRawDemand) -> None:
        self.persisted = persisted
        self.calls: list[tuple[str, object]] = []

    def persist_raw_demand(
        self,
        raw_demand: RawDemand,
        *,
        author_id: object,
        request_id: str | None = None,
    ) -> PersistedRawDemand:
        self.calls.append(("original", (raw_demand.text, author_id, request_id)))
        return self.persisted

    def persist_normalization(
        self,
        raw_input_id: object,
        normalized_content: str,
        *,
        request_id: str | None = None,
    ) -> None:
        self.calls.append(("normalized", (raw_input_id, normalized_content, request_id)))


def test_capture_persists_original_first_and_normalized_text_separately() -> None:
    demand_id = uuid4()
    author_id = uuid4()
    raw_input_id = uuid4()
    original = "[20/09/2026 10:31] Ana: **Curso de vendas** para 20 pessoas."
    raw_demand = RawDemand(
        demand_id=demand_id,
        text=original,
        source_type=SourceKind.MENSAGENS,
    )
    persisted = PersistedRawDemand(
        raw_input_id=raw_input_id,
        demand_id=demand_id,
        source_type=SourceKind.MENSAGENS,
        created_at=datetime.now(UTC),
    )
    pipeline = PipelineClientSpy(persisted)

    result = IngestionService(pipeline).capture(
        raw_demand,
        author_id=author_id,
        request_id="rf11-test",
    )

    assert result is persisted
    assert pipeline.calls == [
        ("original", (original, author_id, "rf11-test")),
        ("normalized", (raw_input_id, "Curso de vendas para 20 pessoas.", "rf11-test")),
    ]
    assert raw_demand.text == original
