"""Persistencia e consulta de demandas, sem encerrar a transacao (RF02, RF03)."""

from collections.abc import Mapping
from datetime import datetime
from typing import Any
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Session, selectinload

from app.domain.enums import DemandStatus, PipelineStage
from app.models.artifact import Artifact
from app.models.demand import Demand


class DemandRepository:
    """Isola escrita, filtros combinaveis e paginacao de demandas."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, demand: Demand) -> Demand:
        """Insere e valida as restricoes antes de produzir a resposta HTTP."""

        self.session.add(demand)
        self.session.flush()
        self.session.refresh(demand)
        return demand

    def list(
        self,
        *,
        client_id: UUID | None = None,
        stage: PipelineStage | None = None,
        owner_id: UUID | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        status: DemandStatus | None = None,
        limit: int,
        offset: int,
    ) -> tuple[list[Demand], int]:
        """Lista demandas com filtros em AND e total antes do recorte da pagina."""

        filters: list[sa.ColumnElement[bool]] = []
        if client_id is not None:
            filters.append(Demand.client_id == client_id)
        if stage is not None:
            filters.append(Demand.current_stage == stage.value)
        if owner_id is not None:
            filters.append(Demand.owner_id == owner_id)
        if created_from is not None:
            filters.append(Demand.created_at >= created_from)
        if created_to is not None:
            filters.append(Demand.created_at <= created_to)
        if status is not None:
            filters.append(Demand.status == status.value)

        total_statement = sa.select(sa.func.count(Demand.id)).where(*filters)
        total = self.session.scalar(total_statement) or 0

        items_statement = (
            sa.select(Demand)
            .where(*filters)
            .order_by(Demand.created_at.desc(), Demand.id.desc())
            .offset(offset)
            .limit(limit)
        )
        items = list(self.session.scalars(items_statement).all())
        return items, total

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
