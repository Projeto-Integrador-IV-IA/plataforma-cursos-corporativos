"""Gatilho de embeddings apos a estruturacao (card #160, RF29).

Sem isso a rota de embeddagem existe mas nada a aciona em producao (ver
ADR-0007). O gatilho e melhor esforco de proposito: a execucao ja entregou o
que RF17 promete (o curso estruturado), e o indice de recuperacao e uma
derivacao posterior que nao pode reabrir a execucao como falha.
"""

import asyncio

from app.domain.jobs import JobStatus
from app.providers import MockLLMProvider
from app.services.job_service import StructuringJobService
from app.services.structuring_service import DEFAULT_PROMPT_VERSION, RawDemand, StructuringService
from tests.conftest import MakeSettings


class _PipelineClientFalso:
    """Confirma a persistencia do artefato sem rede, como RF13 exige para concluir."""

    async def find_artifact_id(self, demand_id: str, artifact_type: str) -> str | None:
        return None

    async def persist_artifact(self, demand_id: str, payload: dict) -> None:
        pass


class _EmbeddingServiceFalso:
    def __init__(self, *, erro: Exception | None = None) -> None:
        self.erro = erro
        self.chamadas: list[str] = []

    async def embed_demand(self, demand_id: str) -> None:
        self.chamadas.append(demand_id)
        if self.erro is not None:
            raise self.erro


async def _submeter_e_aguardar_desfecho(jobs: StructuringJobService, demand: RawDemand) -> None:
    job = jobs.submit(demand, prompt_version=DEFAULT_PROMPT_VERSION)
    for _ in range(200):
        if jobs.get(job.id).status in {JobStatus.CONCLUIDA, JobStatus.ERRO}:
            return job.id
        await asyncio.sleep(0)
    raise AssertionError("a execucao nao chegou a um desfecho")


def test_embeddings_sao_gerados_apos_a_estruturacao_concluir(
    make_settings: MakeSettings,
) -> None:
    settings = make_settings()
    service = StructuringService(MockLLMProvider(model="mock"), settings)
    embedding_service = _EmbeddingServiceFalso()
    jobs = StructuringJobService(
        service,
        pipeline_service_url=settings.pipeline_service_url,
        embedding_service=embedding_service,
    )
    jobs._pipeline_client = _PipelineClientFalso()  # type: ignore[assignment]

    demand = RawDemand(demand_id="dem-1", text="Curso de NR-12.", source_ids=("src-1",))
    job_id = asyncio.run(_submeter_e_aguardar_desfecho(jobs, demand))

    assert jobs.get(job_id).status == JobStatus.CONCLUIDA
    assert embedding_service.chamadas == ["dem-1"]


def test_falha_ao_gerar_embeddings_nao_derruba_a_execucao_concluida(
    make_settings: MakeSettings,
) -> None:
    settings = make_settings()
    service = StructuringService(MockLLMProvider(model="mock"), settings)
    embedding_service = _EmbeddingServiceFalso(erro=RuntimeError("provedor de embedding fora"))
    jobs = StructuringJobService(
        service,
        pipeline_service_url=settings.pipeline_service_url,
        embedding_service=embedding_service,
    )
    jobs._pipeline_client = _PipelineClientFalso()  # type: ignore[assignment]

    demand = RawDemand(demand_id="dem-2", text="Curso de NR-12.", source_ids=("src-1",))
    job_id = asyncio.run(_submeter_e_aguardar_desfecho(jobs, demand))

    assert jobs.get(job_id).status == JobStatus.CONCLUIDA
    assert embedding_service.chamadas == ["dem-2"]


def test_sem_servico_de_embedding_a_execucao_conclui_normalmente(
    make_settings: MakeSettings,
) -> None:
    settings = make_settings()
    service = StructuringService(MockLLMProvider(model="mock"), settings)
    jobs = StructuringJobService(service, pipeline_service_url=settings.pipeline_service_url)
    jobs._pipeline_client = _PipelineClientFalso()  # type: ignore[assignment]

    demand = RawDemand(demand_id="dem-3", text="Curso de NR-12.", source_ids=("src-1",))
    job_id = asyncio.run(_submeter_e_aguardar_desfecho(jobs, demand))

    assert jobs.get(job_id).status == JobStatus.CONCLUIDA
