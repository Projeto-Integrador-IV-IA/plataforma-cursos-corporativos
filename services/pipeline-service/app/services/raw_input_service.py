"""Caso de uso de preservacao do texto bruto antes do processamento (RF09)."""

import sqlite3
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.models import Demand, RawInput, User
from app.repositories.raw_input_repository import RawInputRepository
from app.schemas.raw_input import RawInputCreate, RawInputNormalization


class RawInputService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = RawInputRepository(session)

    def create(self, demand_id: UUID, author_id: UUID, data: RawInputCreate) -> RawInput:
        if self.session.get(Demand, demand_id) is None:
            raise NotFoundError(
                code="DEMAND_NOT_FOUND",
                message="Demanda nao encontrada.",
                details={"demand_id": str(demand_id)},
            )
        if self.session.get(User, author_id) is None:
            raise NotFoundError(
                code="USER_NOT_FOUND",
                message="Operador nao encontrado.",
                details={"author_id": str(author_id)},
            )

        raw_input = RawInput(
            demand_id=demand_id,
            author_id=author_id,
            original_content=data.original_content,
            source=data.source.value,
        )
        try:
            return self.repository.create(raw_input)
        except IntegrityError as exc:
            self.session.rollback()
            is_foreign_key_error = (
                getattr(exc.orig, "sqlstate", None) == "23503"
                or getattr(exc.orig, "sqlite_errorcode", None)
                == sqlite3.SQLITE_CONSTRAINT_FOREIGNKEY
            )
            if not is_foreign_key_error:
                raise
            raise ConflictError(
                code="RAW_INPUT_REFERENCE_CONFLICT",
                message="A demanda ou o operador deixou de existir durante a persistencia.",
                details={"demand_id": str(demand_id), "author_id": str(author_id)},
            ) from exc

    def normalize(self, raw_input_id: UUID, data: RawInputNormalization) -> RawInput:
        """Preenche somente o campo normalizado e conserva o original imutavel."""

        raw_input = self.session.get(RawInput, raw_input_id)
        if raw_input is None:
            raise NotFoundError(
                code="RAW_INPUT_NOT_FOUND",
                message="Fonte bruta nao encontrada.",
                details={"raw_input_id": str(raw_input_id)},
            )
        return self.repository.update_normalization(raw_input, data.normalized_content)
