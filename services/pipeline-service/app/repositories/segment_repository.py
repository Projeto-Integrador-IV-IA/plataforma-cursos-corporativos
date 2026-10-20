"""Persistencia e consulta dos trechos vinculados a fontes e demandas."""

from collections.abc import Sequence
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Session, joinedload

from app.models import RawInput, SourceSegment


class SourceSegmentRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def find_collisions(
        self,
        raw_input_id: UUID,
        ids: Sequence[UUID],
        positions: Sequence[int],
    ) -> list[SourceSegment]:
        statement = (
            sa.select(SourceSegment)
            .where(
                sa.or_(
                    SourceSegment.id.in_(ids),
                    sa.and_(
                        SourceSegment.raw_input_id == raw_input_id,
                        SourceSegment.position.in_(positions),
                    ),
                )
            )
            .options(joinedload(SourceSegment.raw_input))
        )
        return list(self.session.scalars(statement).all())

    def create_many(self, segments: Sequence[SourceSegment]) -> None:
        self.session.add_all(segments)
        self.session.flush()

    def list_by_source(self, raw_input_id: UUID) -> list[SourceSegment]:
        statement = (
            sa.select(SourceSegment)
            .where(SourceSegment.raw_input_id == raw_input_id)
            .options(joinedload(SourceSegment.raw_input))
            .order_by(SourceSegment.position)
        )
        return list(self.session.scalars(statement).all())

    def list_by_demand(self, demand_id: UUID) -> list[SourceSegment]:
        statement = (
            sa.select(SourceSegment)
            .join(SourceSegment.raw_input)
            .where(RawInput.demand_id == demand_id)
            .options(joinedload(SourceSegment.raw_input))
            .order_by(RawInput.created_at, RawInput.id, SourceSegment.position)
        )
        return list(self.session.scalars(statement).all())

    def rollback(self) -> None:
        self.session.rollback()
