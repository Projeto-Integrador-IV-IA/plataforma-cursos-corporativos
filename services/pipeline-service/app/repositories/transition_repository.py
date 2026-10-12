"""Persistencia do historico de etapas (RF07, RNF09).

Repositorio append-only: expoe apenas insercao e leituras. Qualquer tentativa
de update ou delete e erro de programacao - o historico e a trilha de auditoria
e precisa permanecer integro. Por isso este modulo nao tem, e nao deve ganhar,
metodo que altere ou apague um evento ja gravado.

Como os demais repositorios, nao encerra a transacao: ``record`` so faz
``flush``. Quem decide o commit e a sessao da requisicao, o que permite ao
servico gravar a transicao e atualizar a demanda de forma atomica.
"""

from uuid import UUID

from sqlalchemy.orm import Session

from app.domain.enums import PipelineStage
from app.models.stage_transition import StageTransition


class TransitionRepository:
    """Escreve eventos de transicao; nao altera nem remove nenhum."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def record(
        self,
        demand_id: UUID,
        from_stage: PipelineStage | None,
        to_stage: PipelineStage,
        reason: str | None,
        author_id: UUID,
    ) -> StageTransition:
        """Insere um evento e valida as restricoes do banco antes de devolver.

        ``occurred_at`` vem do banco (``server_default``); o ``refresh`` o traz
        de volta junto com o ``id`` para o chamador montar a resposta.
        """

        transition = StageTransition(
            demand_id=demand_id,
            from_stage=PipelineStage(from_stage).value if from_stage is not None else None,
            to_stage=PipelineStage(to_stage).value,
            reason=reason,
            author_id=author_id,
        )
        self.session.add(transition)
        self.session.flush()
        self.session.refresh(transition)
        return transition
