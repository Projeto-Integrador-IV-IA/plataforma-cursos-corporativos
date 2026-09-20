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

    def update_normalization(self, raw_input: RawInput, normalized_content: str) -> RawInput:
        raw_input.normalized_content = normalized_content
        self.session.flush()
        self.session.refresh(raw_input)
        return raw_input
