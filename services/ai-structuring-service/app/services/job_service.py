"""Aceite e acompanhamento das execucoes de estruturacao (RF17, RNF06).

O registro vive em memoria, e essa escolha tem consequencias que precisam estar
a vista em vez de escondidas:

- reiniciar o processo perde as execucoes em andamento;
- com mais de uma replica, o identificador devolvido por uma so e encontrado
  nela.

Nenhuma das duas e aceitavel em producao, e nenhuma e resolvida aqui: o
`ai-structuring-service` nao tem banco proprio e nao acessa o banco de outro
servico (ADR-0001). A persistencia da execucao pertence ao pipeline-service,
junto do artefato (RF13). O que **nao** se perde em nenhum dos dois casos e a
demanda bruta, que o ingestion-service ja gravou antes de chamar a IA (RNF05):
o custo de uma execucao perdida e reprocessar, nunca perder o texto do cliente.
"""

import asyncio
import logging
from collections import OrderedDict
from datetime import UTC, datetime
from typing import ClassVar
from uuid import UUID

from app.core.exceptions import LLMProviderError, PlatformError
from app.domain.jobs import JobStatus, StructuringJob
from app.services.structuring_service import RawDemand, StructuringService

_logger = logging.getLogger(__name__)

#: Execucoes mantidas no registro. Passado o teto, a mais antiga sai: sem
#: limite, um servico de longa duracao acumularia todo resultado ja produzido.
MAX_JOBS_IN_MEMORY = 500


class JobNotFoundError(PlatformError):
    """Identificador de execucao desconhecido neste processo."""

    code: ClassVar[str] = "STRUCTURING_JOB_NOT_FOUND"
    http_status: ClassVar[int] = 404


class StructuringJobService:
    """Aceita o pedido, processa fora do ciclo da requisicao e guarda o estado."""

    def __init__(self, structuring_service: StructuringService) -> None:
        self.structuring_service = structuring_service
        self._jobs: OrderedDict[UUID, StructuringJob] = OrderedDict()
        self._tasks: set[asyncio.Task[None]] = set()

    def submit(self, demand: RawDemand, *, prompt_version: str | None = None) -> StructuringJob:
        """Registra a execucao e devolve o identificador sem esperar o resultado."""

        job = StructuringJob(demand=demand, prompt_version=prompt_version)
        self._jobs[job.id] = job
        self._descartar_excedente()

        task = asyncio.create_task(self._run(job))
        # A referencia forte evita que o coletor de lixo recolha a tarefa antes
        # de ela terminar - asyncio so guarda referencia fraca.
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return job

    def get(self, job_id: UUID) -> StructuringJob:
        """Devolve a execucao ou recusa com o envelope de erro da plataforma."""

        job = self._jobs.get(job_id)
        if job is None:
            raise JobNotFoundError(
                "Execucao de estruturacao nao encontrada. Identificadores nao sobrevivem "
                "ao reinicio do servico; reprocesse a demanda, que continua preservada."
            )
        return job

    async def _run(self, job: StructuringJob) -> None:
        """Executa a estruturacao e registra o desfecho, qualquer que seja ele."""

        job.status = JobStatus.PROCESSANDO
        job.started_at = datetime.now(UTC)
        assert job.demand is not None

        try:
            outcome = await self.structuring_service.structure_course(
                job.demand,
                prompt_version=job.prompt_version,
            )
        except LLMProviderError as erro:
            self._registrar_falha(job, erro.code, str(erro))
        except Exception as erro:
            _logger.exception(
                "Falha inesperada na execucao da estruturacao (job_id=%s, demand_id=%s).",
                job.id,
                job.demand.demand_id,
            )
            self._registrar_falha(job, "STRUCTURING_FAILED", str(erro))
        else:
            job.outcome = outcome
            if outcome.error is not None:
                self._registrar_falha(job, outcome.error.code, str(outcome.error))
            else:
                job.status = JobStatus.CONCLUIDA
                job.finished_at = datetime.now(UTC)

    @staticmethod
    def _registrar_falha(job: StructuringJob, code: str, message: str) -> None:
        """Fecha a execucao como erro, sem deixar o chamador esperando para sempre."""

        job.status = JobStatus.ERRO
        job.error_code = code
        job.error_message = message
        job.finished_at = datetime.now(UTC)

    def _descartar_excedente(self) -> None:
        """Mantem o registro dentro do teto, descartando as execucoes mais antigas."""

        while len(self._jobs) > MAX_JOBS_IN_MEMORY:
            self._jobs.popitem(last=False)
