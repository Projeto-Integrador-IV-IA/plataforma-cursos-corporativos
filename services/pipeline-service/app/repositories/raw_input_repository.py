"""Persistencia atomica das fontes brutas recebidas pelo pipeline-service."""

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
