"""Execucao de estruturacao acompanhada por identificador (RF17, RNF06).

A estruturacao pode levar dezenas de segundos, e prender a interface nesse
tempo faria o operador achar que o sistema travou. O pedido passa a ser aceito
de imediato, com um identificador, e o estado e consultado depois.

O estado e um ciclo sem volta: ``PENDENTE`` -> ``PROCESSANDO`` -> ``CONCLUIDA``
ou ``ERRO``. Nao ha reabertura - reprocessar cria uma execucao nova, para que o
historico de cada tentativa continue legivel (RNF09).
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from app.services.structuring_service import RawDemand, StructuringOutcome


class JobStatus(StrEnum):
    """Estados possiveis de uma execucao de estruturacao."""

    PENDENTE = "PENDENTE"
    PROCESSANDO = "PROCESSANDO"
    CONCLUIDA = "CONCLUIDA"
    ERRO = "ERRO"


#: Estados a partir dos quais nada mais muda.
ESTADOS_FINAIS = frozenset({JobStatus.CONCLUIDA, JobStatus.ERRO})


@dataclass
class StructuringJob:
    """Uma execucao e tudo o que se sabe sobre ela.

    Attributes:
        id: identificador devolvido ao chamador no aceite.
        demand: demanda que originou a execucao - preservada aqui tambem, para
            que a falha nunca deixe o chamador sem o texto (RNF05).
        prompt_version: versao do prompt pedida, para a execucao ser
            reproduzivel (RNF04).
        status: estado corrente.
        created_at: instante do aceite, base do tempo de ponta a ponta.
        started_at: inicio do processamento; ``None`` enquanto pendente.
        finished_at: fim, em sucesso ou falha.
        outcome: desfecho do caso de uso quando concluiu.
        error_code: codigo tipado da falha, o mesmo do envelope de erro (RNF02).
        error_message: mensagem correspondente.
    """

    id: UUID = field(default_factory=uuid4)
    demand: RawDemand | None = None
    prompt_version: str | None = None
    status: JobStatus = JobStatus.PENDENTE
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    started_at: datetime | None = None
    finished_at: datetime | None = None
    outcome: StructuringOutcome | None = None
    error_code: str | None = None
    error_message: str | None = None

    @property
    def finished(self) -> bool:
        """Informa se a execucao ja chegou a um estado final."""

        return self.status in ESTADOS_FINAIS

    @property
    def total_elapsed_ms(self) -> float | None:
        """Tempo de ponta a ponta, do aceite ate o desfecho.

        Diferente do ``elapsed_ms`` do desfecho, que mede so a chamada ao
        provedor: aqui entra tambem a espera na fila. E este o numero que se
        compara ao limite acordado para a experiencia do operador (RNF06).
        """

        if self.finished_at is None:
            return None
        return (self.finished_at - self.created_at).total_seconds() * 1000
