"""Decisao entre criar e reprocessar o artefato apos a estruturacao (RF08, RF13, RF17).

Achado ao vivo em 18/11/2026: rodar "Fazer o curso com IA" duas vezes para a
mesma demanda criava um artefato irmao a cada vez, em vez de uma nova versao
do mesmo artefato - o metodo `reprocess` do pipeline-service ja existia e ja
tinha teste proprio, mas o job_service nunca o chamava. Estes testes cobrem a
consulta que decide qual dos dois caminhos seguir.
"""

import asyncio

from app.domain.jobs import JobStatus
from app.providers import MockLLMProvider
from app.services.job_service import StructuringJobService
from app.services.structuring_service import DEFAULT_PROMPT_VERSION, RawDemand, StructuringService
from tests.conftest import MakeSettings


class _PipelineClientRegistrador:
    """Registra qual operacao o job_service escolheu, sem rede."""

    def __init__(self, *, artifact_id_existente: str | None) -> None:
        self._artifact_id_existente = artifact_id_existente
        self.chamadas_create: list[tuple[str, dict]] = []
        self.chamadas_reprocess: list[tuple[str, dict]] = []
        self.consultas: list[tuple[str, str]] = []

    async def find_artifact_id(self, demand_id: str, artifact_type: str) -> str | None:
        self.consultas.append((demand_id, artifact_type))
        return self._artifact_id_existente

    async def persist_artifact(self, demand_id: str, payload: dict) -> None:
        self.chamadas_create.append((demand_id, payload))

    async def reprocess_artifact(self, artifact_id: str, payload: dict) -> None:
        self.chamadas_reprocess.append((artifact_id, payload))


async def _submeter_e_aguardar_desfecho(jobs: StructuringJobService, demand: RawDemand) -> None:
    job = jobs.submit(demand, prompt_version=DEFAULT_PROMPT_VERSION)
    for _ in range(200):
        if jobs.get(job.id).status in {JobStatus.CONCLUIDA, JobStatus.ERRO}:
            return job.id
        await asyncio.sleep(0)
    raise AssertionError("a execucao nao chegou a um desfecho")


def _jobs_com_cliente_falso(make_settings: MakeSettings, pipeline_client):
    settings = make_settings()
    service = StructuringService(MockLLMProvider(model="mock"), settings)
    jobs = StructuringJobService(service, pipeline_service_url=settings.pipeline_service_url)
    jobs._pipeline_client = pipeline_client  # type: ignore[assignment]
    return jobs


def test_primeira_estruturacao_da_demanda_cria_artefato_novo(make_settings: MakeSettings) -> None:
    pipeline_client = _PipelineClientRegistrador(artifact_id_existente=None)
    jobs = _jobs_com_cliente_falso(make_settings, pipeline_client)

    demand = RawDemand(demand_id="dem-sem-artefato", text="Curso de NR-12.", source_ids=("src-1",))
    job_id = asyncio.run(_submeter_e_aguardar_desfecho(jobs, demand))

    assert jobs.get(job_id).status == JobStatus.CONCLUIDA
    assert pipeline_client.consultas == [("dem-sem-artefato", "REQUISITOS_EXTRAIDOS")]
    assert len(pipeline_client.chamadas_create) == 1
    assert pipeline_client.chamadas_reprocess == []
    _demand_id, payload = pipeline_client.chamadas_create[0]
    assert payload["type"] == "REQUISITOS_EXTRAIDOS"
    assert payload["title"] == "Estrutura do curso gerada por IA"


def test_segunda_estruturacao_da_mesma_demanda_reprocessa_o_artefato_existente(
    make_settings: MakeSettings,
) -> None:
    pipeline_client = _PipelineClientRegistrador(artifact_id_existente="artefato-ja-existente")
    jobs = _jobs_com_cliente_falso(make_settings, pipeline_client)

    demand = RawDemand(demand_id="dem-com-artefato", text="Curso de NR-12.", source_ids=("src-1",))
    job_id = asyncio.run(_submeter_e_aguardar_desfecho(jobs, demand))

    assert jobs.get(job_id).status == JobStatus.CONCLUIDA
    assert pipeline_client.chamadas_create == []
    assert len(pipeline_client.chamadas_reprocess) == 1
    artifact_id, payload = pipeline_client.chamadas_reprocess[0]
    assert artifact_id == "artefato-ja-existente"
    assert "type" not in payload
    assert "title" not in payload
    assert payload["raw_input_ids"] == ["src-1"]
