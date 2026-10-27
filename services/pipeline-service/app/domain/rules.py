"""Regras de transicao do pipeline (RF05, RF06).

Este modulo e a fonte unica da maquina de estados: avancos sao sequenciais,
retrocessos podem alcancar qualquer etapa anterior e demandas encerradas nao
mudam de etapa. A persistencia da trilha de auditoria pertence ao servico de
aplicacao (RF07), nao a estas funcoes puras.

Permanecer na mesma etapa e transicao invalida, nao no-op: o banco tambem a
recusa, pelo ``CHECK ck_stage_transitions_distinct_stages``. Cabe ao chamador
verificar antes se a demanda ja esta na etapa pedida, quando quiser responder
"nada a fazer" em vez de "movimento proibido".

As funcoes tem contratos diferentes de proposito:

    ``can_transition``        predicado de borda - valor desconhecido devolve
                              False;
    ``available_transitions`` destinos permitidos a partir de uma etapa, na
                              ordem do fluxo - valor desconhecido devolve ();
    ``validate_transition``   o mesmo veredito de ``can_transition``, mas
                              recusando com ``InvalidTransitionError`` que diz
                              o motivo;
    ``advance_target``        destino do avanco ja validado, ou recusa;
    ``next_stage``            navegacao na ordem - valor desconhecido levanta
                              ``ValueError`` e o status nao e considerado.

``can_transition`` e a unica fonte do veredito: ``available_transitions`` e
``validate_transition`` derivam dele, entao a API e a interface nunca discordam.
Estas funcoes sao puras - nao leem nem gravam nada.
"""

from collections.abc import Mapping
from types import MappingProxyType
from typing import Any, Final

from app.core.exceptions import InvalidTransitionError
from app.domain.enums import DemandStatus, PipelineStage

VALID_TRANSITIONS: Final[Mapping[PipelineStage, frozenset[PipelineStage]]] = MappingProxyType(
    {
        PipelineStage.CAPTACAO: frozenset({PipelineStage.ESTRUTURACAO}),
        PipelineStage.ESTRUTURACAO: frozenset(
            {
                PipelineStage.CAPTACAO,
                PipelineStage.PRODUTO,
            }
        ),
        PipelineStage.PRODUTO: frozenset(
            {
                PipelineStage.CAPTACAO,
                PipelineStage.ESTRUTURACAO,
                PipelineStage.PROPOSTA,
            }
        ),
        PipelineStage.PROPOSTA: frozenset(
            {
                PipelineStage.CAPTACAO,
                PipelineStage.ESTRUTURACAO,
                PipelineStage.PRODUTO,
                PipelineStage.ACOMPANHAMENTO,
            }
        ),
        PipelineStage.ACOMPANHAMENTO: frozenset(
            {
                PipelineStage.CAPTACAO,
                PipelineStage.ESTRUTURACAO,
                PipelineStage.PRODUTO,
                PipelineStage.PROPOSTA,
            }
        ),
    }
)


def can_transition(
    current: PipelineStage | str,
    target: PipelineStage | str,
    status: DemandStatus | str = DemandStatus.ABERTA,
) -> bool:
    """Informa se uma demanda pode sair de ``current`` para ``target``.

    Valores desconhecidos sao tratados como transicoes invalidas para que a
    validacao de dominio possa ser usada com seguranca nas bordas da aplicacao.
    Uma etapa ausente de ``VALID_TRANSITIONS`` tambem nao autoriza nada, em vez
    de quebrar o chamador.
    """

    try:
        current_stage = PipelineStage(current)
        target_stage = PipelineStage(target)
        demand_status = DemandStatus(status)
    except ValueError:
        return False

    allowed = VALID_TRANSITIONS.get(current_stage, frozenset())
    return demand_status is DemandStatus.ABERTA and target_stage in allowed


def next_stage(current: PipelineStage | str) -> PipelineStage | None:
    """Retorna a proxima etapa do fluxo ou ``None`` na etapa final.

    Responde apenas pela ordem das etapas: nao consulta o status da demanda e
    nao autoriza a movimentacao. Quem for de fato mover a demanda ainda precisa
    passar o destino por ``can_transition``. Etapa desconhecida e erro de
    programacao e levanta ``ValueError``.
    """

    current_stage = PipelineStage(current)
    stages = tuple(PipelineStage)
    current_index = stages.index(current_stage)

    if current_index == len(stages) - 1:
        return None

    return stages[current_index + 1]


def available_transitions(
    current: PipelineStage | str,
    status: DemandStatus | str = DemandStatus.ABERTA,
) -> tuple[PipelineStage, ...]:
    """Destinos permitidos a partir de ``current``, na ordem do fluxo.

    Serve a interface para habilitar so o que vale. Demanda encerrada nao tem
    destino algum; valor desconhecido tambem devolve ``()``, como
    ``can_transition``. Nunca inclui a propria etapa corrente.
    """

    return tuple(stage for stage in PipelineStage if can_transition(current, stage, status))


def validate_transition(
    current: PipelineStage | str,
    target: PipelineStage | str,
    status: DemandStatus | str = DemandStatus.ABERTA,
) -> None:
    """Recusa com ``InvalidTransitionError`` quando ``can_transition`` diria nao.

    Nao devolve nada quando a transicao vale. O erro explica o motivo, e o
    ``details`` traz a etapa atual, o destino pedido e os destinos permitidos.
    """

    if can_transition(current, target, status):
        return

    raise _refusal(current, target, status)


def advance_target(
    current: PipelineStage | str,
    status: DemandStatus | str = DemandStatus.ABERTA,
) -> PipelineStage:
    """Destino do avanco a partir de ``current``, ja validado.

    Recusa na ultima etapa (``DEMAND_AT_FINAL_STAGE``) antes de olhar o status,
    e depois pela mesma regra de ``validate_transition``. Etapa desconhecida e
    erro de programacao e levanta ``ValueError``, como em ``next_stage``.
    """

    target = next_stage(current)
    if target is None:
        current_stage = PipelineStage(current)
        raise InvalidTransitionError(
            code="DEMAND_AT_FINAL_STAGE",
            message=(
                f"A demanda ja esta na ultima etapa ({current_stage.value}) e nao pode avancar."
            ),
            details={"current_stage": current_stage.value},
        )

    validate_transition(current, target, status)
    return target


def _refusal(
    current: PipelineStage | str,
    target: PipelineStage | str,
    status: DemandStatus | str,
) -> InvalidTransitionError:
    """Explica por que ``can_transition`` recusou; sempre devolve um erro."""

    try:
        current_stage = PipelineStage(current)
        target_stage = PipelineStage(target)
        demand_status = DemandStatus(status)
    except ValueError:
        return InvalidTransitionError(
            code="INVALID_STAGE_TRANSITION",
            message="Etapa ou situacao desconhecida.",
            details={
                "current_stage": str(current),
                "target_stage": str(target),
                "status": str(status),
            },
        )

    details: dict[str, Any] = {
        "current_stage": current_stage.value,
        "target_stage": target_stage.value,
        "allowed_stages": [stage.value for stage in available_transitions(current_stage, status)],
    }

    if demand_status is not DemandStatus.ABERTA:
        details["status"] = demand_status.value
        return InvalidTransitionError(
            code="DEMAND_NOT_OPEN",
            message="Demandas encerradas nao mudam de etapa.",
            details=details,
        )

    if current_stage is target_stage:
        return InvalidTransitionError(
            code="STAGE_UNCHANGED",
            message=f"A demanda ja esta na etapa {current_stage.value}; escolha outra etapa.",
            details=details,
        )

    message = f"Transicao de {current_stage.value} para {target_stage.value} nao e permitida."
    stages = tuple(PipelineStage)
    following = next_stage(current_stage)
    if following is not None and stages.index(target_stage) > stages.index(current_stage):
        message += f" O avanco e sequencial: a proxima etapa e {following.value}."

    return InvalidTransitionError(
        code="INVALID_STAGE_TRANSITION",
        message=message,
        details=details,
    )
