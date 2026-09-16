"""Regras de transicao do pipeline (RF05, RF06).

Este modulo e a fonte unica da maquina de estados: avancos sao sequenciais,
retrocessos podem alcançar qualquer etapa anterior e demandas encerradas nao
mudam de etapa. A persistencia da trilha de auditoria pertence ao servico de
aplicacao (RF07), nao a estas funcoes puras.
"""

from collections.abc import Mapping
from types import MappingProxyType
from typing import Final

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
    """

    try:
        current_stage = PipelineStage(current)
        target_stage = PipelineStage(target)
        demand_status = DemandStatus(status)
    except ValueError:
        return False

    return demand_status is DemandStatus.ABERTA and target_stage in VALID_TRANSITIONS[current_stage]


def next_stage(current: PipelineStage | str) -> PipelineStage | None:
    """Retorna a proxima etapa do fluxo ou ``None`` na etapa final."""

    current_stage = PipelineStage(current)
    stages = tuple(PipelineStage)
    current_index = stages.index(current_stage)

    if current_index == len(stages) - 1:
        return None

    return stages[current_index + 1]
