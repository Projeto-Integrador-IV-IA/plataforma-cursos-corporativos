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

from app.core.exceptions import ConflictError, NotFoundError, ValidationError, issue_de_validacao
from app.domain.enums import DemandStatus, PipelineStage
from app.domain.rules import can_transition, next_stage
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

        A etapa de destino nunca vem do chamador: sai de ``next_stage`` e passa
        por ``can_transition``, que tambem barra demandas encerradas.

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
        target = next_stage(current)
        if target is None:
            raise ConflictError(
                code="DEMAND_AT_FINAL_STAGE",
                message=(
                    f"A demanda ja esta na ultima etapa ({current.value}) e nao pode avancar."
                ),
                details={"current_stage": current.value},
            )

        if not can_transition(current, target, demand.status):
            if demand.status != DemandStatus.ABERTA.value:
                raise ConflictError(
                    code="DEMAND_NOT_OPEN",
                    message="Demandas encerradas nao mudam de etapa.",
                    details={"status": demand.status},
                )
            raise ConflictError(
                code="INVALID_STAGE_TRANSITION",
                message=f"Transicao de {current.value} para {target.value} nao e permitida.",
                details={"current_stage": current.value, "target_stage": target.value},
            )

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

    def rollback(
        self,
        demand_id: UUID,
        to_stage: PipelineStage,
        author_id: UUID,
        reason: str,
    ) -> StageChangeRead:
        """Retrocede a qualquer etapa anterior sem alterar o agregado da demanda.

        Somente ``current_stage`` e ``updated_at`` mudam na demanda. Fontes,
        artefatos e eventos anteriores nao sao atualizados nem removidos; um novo
        evento append-only registra o retrocesso na mesma transacao.
        """

        normalized_reason = reason.strip() if isinstance(reason, str) else ""
        if not normalized_reason:
            raise ValidationError(
                code="ROLLBACK_REASON_REQUIRED",
                message="A justificativa do retrocesso e obrigatoria.",
                details={
                    "issues": [
                        issue_de_validacao(
                            localizacao=["body", "reason"],
                            mensagem="A justificativa do retrocesso e obrigatoria.",
                            tipo="value_error",
                        )
                    ]
                },
            )
        if len(normalized_reason) > 1000:
            raise ValidationError(
                code="ROLLBACK_REASON_TOO_LONG",
                message="A justificativa do retrocesso deve ter no maximo 1000 caracteres.",
                details={
                    "issues": [
                        issue_de_validacao(
                            localizacao=["body", "reason"],
                            mensagem="A justificativa deve ter no maximo 1000 caracteres.",
                            tipo="string_too_long",
                        )
                    ]
                },
            )

        demand = self.repository.get_for_update(demand_id)
        if demand is None:
            raise NotFoundError(code="DEMAND_NOT_FOUND", message="Demanda nao encontrada.")
        if self.session.get(User, author_id) is None:
            raise NotFoundError(code="USER_NOT_FOUND", message="Operador nao encontrado.")

        current = PipelineStage(demand.current_stage)
        target = PipelineStage(to_stage)
        stages = tuple(PipelineStage)
        if stages.index(target) >= stages.index(current):
            raise ConflictError(
                code="ROLLBACK_TARGET_NOT_PREVIOUS",
                message=(
                    f"O retrocesso de {current.value} para {target.value} nao e permitido: "
                    "o destino deve ser uma etapa anterior."
                ),
                details={"current_stage": current.value, "target_stage": target.value},
            )

        if not can_transition(current, target, demand.status):
            if demand.status != DemandStatus.ABERTA.value:
                raise ConflictError(
                    code="DEMAND_NOT_OPEN",
                    message="Demandas encerradas nao mudam de etapa.",
                    details={"status": demand.status},
                )
            raise ConflictError(
                code="INVALID_STAGE_TRANSITION",
                message=f"Transicao de {current.value} para {target.value} nao e permitida.",
                details={"current_stage": current.value, "target_stage": target.value},
            )

        transition = self.transitions.record(
            demand.id,
            current,
            target,
            normalized_reason,
            author_id,
        )
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
