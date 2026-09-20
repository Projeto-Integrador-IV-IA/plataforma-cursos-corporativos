"""Persistencia e consulta de demandas, sem encerrar a transacao (RF02)."""

from collections.abc import Mapping
from typing import Any
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Session, selectinload

from app.models.artifact import Artifact
from app.models.demand import Demand


class DemandRepository:
    """Isola a escrita e recupera os valores gerados pelo banco."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, demand: Demand) -> Demand:
        """Insere e valida as restricoes antes de produzir a resposta HTTP."""

        self.session.add(demand)
        self.session.flush()
        self.session.refresh(demand)
        return demand

    def get_detail(self, demand_id: UUID) -> Demand | None:
        """Carrega o agregado necessario pela tela em consultas agrupadas."""

        statement = (
            sa.select(Demand)
            .where(Demand.id == demand_id)
            .options(
                selectinload(Demand.client),
                selectinload(Demand.artifacts).selectinload(Artifact.versions),
            )
        )
        return self.session.scalar(statement)

    def update(self, demand: Demand, changes: Mapping[str, Any]) -> Demand:
        """Aplica apenas campos explicitamente enviados no PATCH."""

        for field, value in changes.items():
            setattr(demand, field, value)
        self.session.flush()
        self.session.refresh(demand)
        return demand
