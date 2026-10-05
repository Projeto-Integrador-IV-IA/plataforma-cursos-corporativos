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

    @staticmethod
    def _filters(
        *,
        client_id: UUID | None,
        stage: PipelineStage | None,
        owner_id: UUID | None,
        created_from: datetime | None,
        created_to: datetime | None,
        status: DemandStatus | None,
    ) -> list["sa.ColumnElement[bool]"]:
        """Monta os filtros em AND usados pela listagem (RF03) e pelo quadro (RF05).

        Um lugar so: se a listagem e o quadro filtrassem por caminhos
        diferentes, o total de uma etapa no quadro poderia discordar do total
        que a listagem devolve para a mesma etapa.
        """

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
        return filters

    # Definido antes de ``list`` de proposito: o metodo ``list`` sombreia o
    # builtin dentro do corpo da classe, e uma anotacao ``list[...]`` escrita
    # depois dele resolveria para o metodo em vez do tipo.
    def list_for_board(
        self,
        *,
        stage: PipelineStage,
        client_id: UUID | None = None,
        owner_id: UUID | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        status: DemandStatus | None = None,
        limit: int,
    ) -> tuple[list[Demand], int]:
        """Cartoes de uma etapa do quadro, com o total antes do recorte (RF05).

        Carrega cliente e responsavel junto: o cartao mostra os dois nomes, e
        sem isso a montagem do quadro faria uma consulta por demanda.
        """

        filters = self._filters(
            client_id=client_id,
            stage=stage,
            owner_id=owner_id,
            created_from=created_from,
            created_to=created_to,
            status=status,
        )

        total = self.session.scalar(sa.select(sa.func.count(Demand.id)).where(*filters)) or 0
        items_statement = (
            sa.select(Demand)
            .where(*filters)
            .options(selectinload(Demand.client), selectinload(Demand.owner))
            .order_by(Demand.created_at.desc(), Demand.id.desc())
            .limit(limit)
        )
        return list(self.session.scalars(items_statement).all()), total

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

        filters = self._filters(
            client_id=client_id,
            stage=stage,
            owner_id=owner_id,
            created_from=created_from,
            created_to=created_to,
            status=status,
        )

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
                selectinload(Demand.raw_inputs),
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
