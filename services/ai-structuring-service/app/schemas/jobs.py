"""DTOs do acompanhamento de execucao da estruturacao (RF17, RNF06).

O aceite devolve o minimo para acompanhar; a consulta devolve o estado e, so
quando concluiu, o resultado. Nada de "resultado parcial": enquanto a execucao
nao terminou nao ha curso nenhum para mostrar, e devolver um esqueleto vazio
faria a tela exibir campos que ninguem preencheu (RNF03).
"""

from datetime import datetime
from typing import Any, Final, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.domain.jobs import JobStatus, StructuringJob
from app.schemas.structuring import ExecutionMetadata, StructuringResponse

#: Aceite de exemplo exibido no Swagger. Dado ficticio - nenhum cliente real (RNF10).
EXEMPLO_DE_ACEITE: Final[dict[str, Any]] = {
    "job_id": "3f1c2a54-9a1b-4f0e-8a77-0b9f1c2d3e4f",
    "demand_id": "dem-2026-0042",
    "status": "PENDENTE",
    "created_at": "2026-09-22T10:00:00Z",
}


class StructuringJobAccepted(BaseModel):
    """Confirmacao de que o pedido entrou na fila, sem esperar o resultado."""

    model_config = ConfigDict(frozen=True, json_schema_extra={"examples": [EXEMPLO_DE_ACEITE]})

    job_id: UUID
    demand_id: str
    status: JobStatus
    created_at: datetime

    @classmethod
    def from_job(cls, job: StructuringJob) -> Self:
        assert job.demand is not None
        return cls(
            job_id=job.id,
            demand_id=job.demand.demand_id,
            status=job.status,
            created_at=job.created_at,
        )


class StructuringJobError(BaseModel):
    """Falha que encerrou a execucao, no mesmo vocabulario do envelope (RNF02)."""

    model_config = ConfigDict(frozen=True)

    code: str
    message: str


class StructuringJobRead(BaseModel):
    """Estado da execucao e, quando houver, o que ela produziu.

    ``total_elapsed_ms`` mede do aceite ao desfecho, incluindo a espera na
    fila - e diferente do ``elapsed_ms`` de ``execution``, que mede so a
    chamada ao provedor. O primeiro e o tempo que o operador sente (RNF06); o
    segundo e o que se compara entre modelos (RNF04).
    """

    model_config = ConfigDict(frozen=True)

    job_id: UUID
    demand_id: str
    status: JobStatus
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    total_elapsed_ms: float | None
    result: StructuringResponse | None
    execution: ExecutionMetadata | None
    error: StructuringJobError | None

    @classmethod
    def from_job(cls, job: StructuringJob) -> Self:
        assert job.demand is not None

        resultado: StructuringResponse | None = None
        execucao: ExecutionMetadata | None = None
        if job.status is JobStatus.CONCLUIDA and job.outcome is not None:
            resultado = StructuringResponse.from_outcome(job.outcome)
            execucao = resultado.execution

        erro: StructuringJobError | None = None
        if job.error_code is not None:
            erro = StructuringJobError(code=job.error_code, message=job.error_message or "")

        return cls(
            job_id=job.id,
            demand_id=job.demand.demand_id,
            status=job.status,
            created_at=job.created_at,
            started_at=job.started_at,
            finished_at=job.finished_at,
            total_elapsed_ms=job.total_elapsed_ms,
            result=resultado,
            execution=execucao,
            error=erro,
        )
