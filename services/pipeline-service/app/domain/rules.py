"""Regras de transicao do pipeline (RF05, RF06).

Este modulo e a fonte unica da maquina de estados: avancos sao sequenciais,
retrocessos podem alcancar qualquer etapa anterior e demandas encerradas nao
mudam de etapa. A persistencia da trilha de auditoria pertence ao servico de
aplicacao (RF07), nao a estas funcoes puras.

Permanecer na mesma etapa e transicao invalida, nao no-op: o banco tambem a
recusa, pelo ``CHECK ck_stage_transitions_distinct_stages``. Cabe ao chamador
verificar antes se a demanda ja esta na etapa pedida, quando quiser responder
"nada a fazer" em vez de "movimento proibido".

As duas funcoes tem contratos diferentes de proposito:

    ``can_transition``  predicado de borda - valor desconhecido devolve False;
    ``next_stage``      navegacao na ordem - valor desconhecido levanta
                        ``ValueError`` e o status nao e considerado.
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
