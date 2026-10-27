"""Persistencia atomica das fontes brutas recebidas pelo pipeline-service."""

from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.models.raw_input import RawInput


class RawInputRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, raw_input: RawInput) -> RawInput:
        self.session.add(raw_input)
        self.session.flush()
        self.session.refresh(raw_input)
        return raw_input

    def next_received_order(self, demand_id: UUID) -> int:
        """Calcula a sequencia sob bloqueio da demanda mantido pelo caso de uso."""

        last = self.session.scalar(
            sa.select(sa.func.max(RawInput.received_order)).where(RawInput.demand_id == demand_id)
        )
        return (last or 0) + 1

    def update_normalization(self, raw_input: RawInput, normalized_content: str) -> RawInput:
        raw_input.normalized_content = normalized_content
        self.session.flush()
        self.session.refresh(raw_input)
        return raw_input
