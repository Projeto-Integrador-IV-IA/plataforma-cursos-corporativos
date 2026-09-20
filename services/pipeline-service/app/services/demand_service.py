"""Criacao de negociacoes com cliente obrigatorio (RF02).

O vinculo obrigatorio com o cliente e garantido no banco pelo RNF08 - numerado
como RNF14 no Documento Consolidado v1.0; vale o ID da matriz do repositorio.
"""

import sqlite3
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.enums import DemandStatus, PipelineStage
from app.models import Client, Demand, User
from app.repositories.demand_repository import DemandRepository
from app.schemas.demand import DemandCreate, DemandUpdate


class DemandCreationError(Exception):
    """Falha previsivel de referencia, traduzida pela fronteira HTTP."""

    def __init__(self, status_code: int, code: str, message: str, details: dict[str, str]) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details


class DemandNotFoundError(Exception):
    """Identificador de demanda inexistente."""

    def __init__(self, demand_id: UUID) -> None:
        super().__init__("Demanda nao encontrada.")
        self.status_code = 404
        self.code = "DEMAND_NOT_FOUND"
        self.message = "Demanda nao encontrada."
        self.details = {"demand_id": str(demand_id)}


class DemandService:
    """Demanda nasce ABERTA, em CAPTACAO, vinculada a um cliente existente."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = DemandRepository(session)

    def create(self, data: DemandCreate) -> Demand:
        """Valida referencias e persiste; a FK protege tambem contra concorrencia."""

        if self.session.get(Client, data.client_id) is None:
            raise DemandCreationError(
                404,
                "CLIENT_NOT_FOUND",
                "Cliente nao encontrado.",
                {"client_id": str(data.client_id)},
            )
        if data.owner_id is not None and self.session.get(User, data.owner_id) is None:
            raise DemandCreationError(
                404,
                "USER_NOT_FOUND",
                "Responsavel nao encontrado.",
                {"owner_id": str(data.owner_id)},
            )

        demand = Demand(
            **data.model_dump(),
            status=DemandStatus.ABERTA.value,
            current_stage=PipelineStage.CAPTACAO.value,
        )
        try:
            return self.repository.create(demand)
        except IntegrityError as exc:
            self.session.rollback()
            # Reconhece a categoria de erro, sem interpretar mensagens do driver.
            is_foreign_key_error = (
                getattr(exc.orig, "sqlstate", None) == "23503"
                or getattr(exc.orig, "sqlite_errorcode", None)
                == sqlite3.SQLITE_CONSTRAINT_FOREIGNKEY
            )
            if not is_foreign_key_error:
                raise
            raise DemandCreationError(
                409,
                "DEMAND_REFERENCE_CONFLICT",
                "Cliente ou responsavel deixou de existir durante a criacao da demanda.",
                {"client_id": str(data.client_id)},
            ) from exc

    def get(self, demand_id: UUID) -> Demand:
        """Consulta a demanda com cliente e artefatos vinculados."""

        demand = self.repository.get_detail(demand_id)
        if demand is None:
            raise DemandNotFoundError(demand_id)
        return demand

    def update(self, demand_id: UUID, data: DemandUpdate) -> Demand:
        """Edita somente o contexto informado e preserva todo o restante."""

        demand = self.get(demand_id)
        changes = data.model_dump(exclude_unset=True)
        if not changes:
            return demand
        owner_id = changes.get("owner_id")
        if owner_id is not None and self.session.get(User, owner_id) is None:
            raise DemandCreationError(
                404,
                "USER_NOT_FOUND",
                "Responsavel nao encontrado.",
                {"owner_id": str(owner_id)},
            )
        changes["updated_at"] = datetime.now(UTC)
        return self.repository.update(demand, changes)
