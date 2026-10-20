"""Caso de uso de persistencia imutavel dos trechos de uma fonte."""

import sqlite3
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.models import Demand, RawInput, SourceSegment
from app.repositories.segment_repository import SourceSegmentRepository
from app.schemas.segment import SourceSegmentBatchCreate


class SourceSegmentService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = SourceSegmentRepository(session)

    def persist(
        self,
        raw_input_id: UUID,
        data: SourceSegmentBatchCreate,
    ) -> list[SourceSegment]:
        if self.session.get(RawInput, raw_input_id) is None:
            raise NotFoundError(
                code="RAW_INPUT_NOT_FOUND",
                message="Fonte bruta nao encontrada.",
                details={"raw_input_id": str(raw_input_id)},
            )

        collisions = self.repository.find_collisions(
            raw_input_id,
            [item.id for item in data.segments],
            [item.position for item in data.segments],
        )
        by_id = {segment.id: segment for segment in collisions}
        by_position = {
            segment.position: segment
            for segment in collisions
            if segment.raw_input_id == raw_input_id
        }
        new_segments: list[SourceSegment] = []
        for item in data.segments:
            existing = by_id.get(item.id) or by_position.get(item.position)
            if existing is None:
                new_segments.append(
                    SourceSegment(
                        id=item.id,
                        raw_input_id=raw_input_id,
                        position=item.position,
                        content=item.content,
                    )
                )
                continue
            if (
                existing.id != item.id
                or existing.raw_input_id != raw_input_id
                or existing.position != item.position
                or existing.content != item.content
            ):
                raise ConflictError(
                    code="SOURCE_SEGMENT_CONFLICT",
                    message="O identificador ou a posicao ja pertence a outro trecho.",
                    details={
                        "segment_id": str(item.id),
                        "raw_input_id": str(raw_input_id),
                        "position": str(item.position),
                    },
                )

        try:
            self.repository.create_many(new_segments)
        except IntegrityError as exc:
            self.repository.rollback()
            is_constraint_error = getattr(exc.orig, "sqlstate", None) in {
                "23503",
                "23505",
                "23514",
            } or getattr(exc.orig, "sqlite_errorcode", None) in {
                sqlite3.SQLITE_CONSTRAINT_CHECK,
                sqlite3.SQLITE_CONSTRAINT_FOREIGNKEY,
                sqlite3.SQLITE_CONSTRAINT_UNIQUE,
            }
            if not is_constraint_error:
                raise
            raise ConflictError(
                code="SOURCE_SEGMENT_PERSISTENCE_CONFLICT",
                message="Nao foi possivel persistir os trechos atomicamente.",
                details={"raw_input_id": str(raw_input_id)},
            ) from exc
        return self.repository.list_by_source(raw_input_id)

    def list_by_source(self, raw_input_id: UUID) -> list[SourceSegment]:
        if self.session.get(RawInput, raw_input_id) is None:
            raise NotFoundError(
                code="RAW_INPUT_NOT_FOUND",
                message="Fonte bruta nao encontrada.",
                details={"raw_input_id": str(raw_input_id)},
            )
        return self.repository.list_by_source(raw_input_id)

    def list_by_demand(self, demand_id: UUID) -> list[SourceSegment]:
        if self.session.get(Demand, demand_id) is None:
            raise NotFoundError(
                code="DEMAND_NOT_FOUND",
                message="Demanda nao encontrada.",
                details={"demand_id": str(demand_id)},
            )
        return self.repository.list_by_demand(demand_id)
