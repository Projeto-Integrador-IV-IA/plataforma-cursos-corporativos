"""Caso de uso: visao do pipeline por etapa (RF05).

O quadro responde "como esta o andamento de tudo" numa consulta so. A
movimentacao entre etapas (RF06) e a trilha de alteracoes (RF07) sao outros
cards e continuam fora deste modulo - a maquina de estados que as sustenta
vive em ``app.domain.rules``.

Por que o recorte por etapa existe: sem limite, uma etapa com muitas demandas
levaria o quadro inteiro junto, e o retorno cresceria sem teto (RNF07). Cada
coluna traz ate ``limit`` cartoes e o ``total`` real, que e o numero que a
interface mostra no cabecalho da coluna.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.domain.enums import DemandStatus, PipelineStage
from app.repositories.demand_repository import DemandRepository
from app.schemas.pipeline import PipelineBoard, PipelineCardRead, PipelineStageGroup

#: Cartoes trazidos por coluna quando o chamador nao pede outro recorte.
DEFAULT_CARDS_PER_STAGE = 20


class PipelineService:
    """Monta o quadro a partir dos mesmos filtros da listagem de demandas."""

    def __init__(self, session: Session) -> None:
        self.repository = DemandRepository(session)

    def board(
        self,
        *,
        client_id: UUID | None = None,
        owner_id: UUID | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        status: DemandStatus | None = None,
        limit: int = DEFAULT_CARDS_PER_STAGE,
    ) -> PipelineBoard:
        """Devolve as cinco etapas, cada uma com seus cartoes e seu total.

        Uma consulta por etapa, cada uma ja limitada: o custo e fixo em cinco
        consultas, e nenhuma delas pode trazer a tabela inteira.
        """

        groups: list[PipelineStageGroup] = []
        for stage in PipelineStage:
            demands, total = self.repository.list_for_board(
                stage=stage,
                client_id=client_id,
                owner_id=owner_id,
                created_from=created_from,
                created_to=created_to,
                status=status,
                limit=limit,
            )
            groups.append(
                PipelineStageGroup(
                    stage=stage,
                    total=total,
                    items=[PipelineCardRead.model_validate(demand) for demand in demands],
                )
            )

        return PipelineBoard(stages=groups, total=sum(group.total for group in groups))
