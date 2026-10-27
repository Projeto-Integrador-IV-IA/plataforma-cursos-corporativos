"""Caso de uso: visao do pipeline por etapa (RF05).

O quadro responde "como esta o andamento de tudo" numa consulta so. A
movimentacao entre etapas (RF06) grava a transicao na trilha (RF07) na mesma
transacao em que muda a demanda; retrocesso e consulta do historico sao outros
cards. A maquina de estados que sustenta tudo vive em ``app.domain.rules``.

Por que o recorte por etapa existe: sem limite, uma etapa com muitas demandas
levaria o quadro inteiro junto, e o retorno cresceria sem teto (RNF07). Cada
coluna traz ate ``limit`` cartoes e o ``total`` real, que e o numero que a
interface mostra no cabecalho da coluna.
"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.domain.enums import DemandStatus, PipelineStage
from app.domain.rules import advance_target
from app.models.user import User
from app.repositories.demand_repository import DemandRepository
from app.repositories.transition_repository import TransitionRepository
from app.schemas.pipeline import (
    PipelineBoard,
    PipelineCardRead,
    PipelineStageGroup,
    StageChangeRead,
)

#: Cartoes trazidos por coluna quando o chamador nao pede outro recorte.
DEFAULT_CARDS_PER_STAGE = 20


class PipelineService:
    """Monta o quadro a partir dos mesmos filtros da listagem de demandas."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = DemandRepository(session)
        self.transitions = TransitionRepository(session)

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

    def advance(
        self,
        demand_id: UUID,
        author_id: UUID,
        reason: str | None = None,
    ) -> StageChangeRead:
        """Avanca a demanda para a proxima etapa e registra a transicao (RF06, RF07).

        A etapa de destino nunca vem do chamador: sai de ``advance_target``, que
        aplica a maquina de estados e recusa, com o motivo, a ultima etapa e as
        demandas encerradas.

        Atomicidade: este metodo so faz ``flush``. O commit (ou o rollback, se
        qualquer passo falhar) e da sessao da requisicao, entao a trilha e a
        etapa da demanda sao gravadas juntas ou nenhuma das duas.
        """

        demand = self.repository.get_for_update(demand_id)
        if demand is None:
            raise NotFoundError(code="DEMAND_NOT_FOUND", message="Demanda nao encontrada.")
        if self.session.get(User, author_id) is None:
            raise NotFoundError(code="USER_NOT_FOUND", message="Operador nao encontrado.")

        current = PipelineStage(demand.current_stage)
        target = advance_target(current, demand.status)

        transition = self.transitions.record(demand.id, current, target, reason, author_id)
        self.repository.update(
            demand,
            {"current_stage": target.value, "updated_at": datetime.now(UTC)},
        )

        return StageChangeRead(
            transition_id=transition.id,
            demand_id=demand.id,
            from_stage=current,
            current_stage=target,
            reason=transition.reason,
            author_id=transition.author_id,
            occurred_at=transition.occurred_at,
        )
