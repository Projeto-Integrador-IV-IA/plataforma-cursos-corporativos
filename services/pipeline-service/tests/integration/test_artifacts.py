"""Aceite RF16.1: resultado e fontes persistidos como um unico agregado."""

import sqlite3
from typing import Any
from uuid import UUID

import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Artifact, ArtifactSource, ArtifactVersion, Client, Demand, RawInput, User
from app.repositories.artifact_repository import ArtifactRepository


@pytest.fixture
def demand_with_sources(engine: Engine) -> tuple[UUID, list[UUID]]:
    with Session(engine) as session:
        client = Client(name="Empresa")
        author = User(name="Operador", email="operator@example.com", password_hash="hash")
        session.add_all([client, author])
        session.flush()
        demand = Demand(client_id=client.id, title="Curso de dados")
        session.add(demand)
        session.flush()
        sources = [
            RawInput(
                demand_id=demand.id,
                original_content="E-mail original",
                source="EMAIL",
                author_id=author.id,
            ),
            RawInput(
                demand_id=demand.id,
                original_content="Mensagem original",
                source="MENSAGENS",
                author_id=author.id,
            ),
        ]
        session.add_all(sources)
        session.commit()
        return demand.id, [source.id for source in sources]


def artifact_payload(source_ids: list[UUID]) -> dict[str, Any]:
    return {
        "type": "REQUISITOS_EXTRAIDOS",
        "title": "Estruturacao inicial",
        "raw_output": '{"tema":"Dados","carga_horaria":8}',
        "structured_content": {"tema": "Dados", "carga_horaria": 8},
        "raw_input_ids": [str(source_id) for source_id in source_ids],
        "ai_metadata": {"model": "test-model", "prompt": "extract-requirements.v2"},
    }


def test_persists_and_recovers_raw_structured_result_and_all_sources(
    api: TestClient,
    engine: Engine,
    demand_with_sources: tuple[UUID, list[UUID]],
) -> None:
    demand_id, source_ids = demand_with_sources

    created = api.post(
        f"/api/v1/demands/{demand_id}/artifacts",
        json=artifact_payload(source_ids),
    )

    assert created.status_code == 201
    body = created.json()
    assert {source["id"] for source in body["sources"]} == {str(value) for value in source_ids}
    assert body["versions"][0]["raw_output"] == '{"tema":"Dados","carga_horaria":8}'
    assert body["versions"][0]["structured_content"] == {
        "tema": "Dados",
        "carga_horaria": 8,
    }

    fetched = api.get(f"/api/v1/demands/{demand_id}/artifacts")
    assert fetched.status_code == 200
    assert fetched.json() == [body]

    with Session(engine) as session:
        assert session.scalar(sa.select(sa.func.count(Artifact.id))) == 1
        assert session.scalar(sa.select(sa.func.count(ArtifactVersion.id))) == 1
        assert session.scalar(sa.select(sa.func.count(ArtifactSource.artifact_id))) == 2


def test_rejects_source_from_another_demand_without_partial_write(
    api: TestClient,
    engine: Engine,
    demand_with_sources: tuple[UUID, list[UUID]],
) -> None:
    demand_id, _ = demand_with_sources
    with Session(engine) as session:
        client = session.scalar(sa.select(Client))
        author = session.scalar(sa.select(User))
        other = Demand(client_id=client.id, title="Outra demanda")
        session.add(other)
        session.flush()
        foreign_source = RawInput(
            demand_id=other.id,
            original_content="Fonte de outra demanda",
            source="EMAIL",
            author_id=author.id,
        )
        session.add(foreign_source)
        session.commit()
        foreign_source_id = foreign_source.id

    response = api.post(
        f"/api/v1/demands/{demand_id}/artifacts",
        json=artifact_payload([foreign_source_id]),
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ARTIFACT_SOURCE_DEMAND_MISMATCH"
    with Session(engine) as session:
        assert session.scalar(sa.select(sa.func.count(Artifact.id))) == 0
        assert session.scalar(sa.select(sa.func.count(ArtifactVersion.id))) == 0
        assert session.scalar(sa.select(sa.func.count(ArtifactSource.artifact_id))) == 0


def test_rolls_back_artifact_version_and_links_when_transaction_fails(
    api: TestClient,
    engine: Engine,
    demand_with_sources: tuple[UUID, list[UUID]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    demand_id, source_ids = demand_with_sources

    class ForcedConstraintError(Exception):
        sqlite_errorcode = sqlite3.SQLITE_CONSTRAINT_FOREIGNKEY

    def fail_after_flush(
        repository: ArtifactRepository,
        artifact: Artifact,
        version: ArtifactVersion,
        source_links: list[ArtifactSource],
    ) -> Artifact:
        artifact.versions.append(version)
        artifact.source_links.extend(source_links)
        repository.session.add(artifact)
        repository.session.flush()
        raise IntegrityError("forced failure", {}, ForcedConstraintError())

    monkeypatch.setattr(ArtifactRepository, "create_result", fail_after_flush)
    response = api.post(
        f"/api/v1/demands/{demand_id}/artifacts",
        json=artifact_payload(source_ids),
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ARTIFACT_PERSISTENCE_CONFLICT"
    with Session(engine) as session:
        assert session.scalar(sa.select(sa.func.count(Artifact.id))) == 0
        assert session.scalar(sa.select(sa.func.count(ArtifactVersion.id))) == 0
        assert session.scalar(sa.select(sa.func.count(ArtifactSource.artifact_id))) == 0


def test_swagger_documents_artifact_creation_and_consultation(api: TestClient) -> None:
    document = api.get("/openapi.json").json()
    operations = document["paths"]["/api/v1/demands/{demand_id}/artifacts"]
    assert {"get", "post"} == set(operations)
    assert {"201", "404", "409", "422"} <= set(operations["post"]["responses"])
    assert {"200", "404", "422"} <= set(operations["get"]["responses"])


def test_sources_come_in_the_same_order_from_creation_and_from_the_query(
    api: TestClient, demand_with_sources: tuple[UUID, list[UUID]]
) -> None:
    """Duas rotas, um artefato: a lista de fontes nao pode mudar de ordem entre elas.

    A criacao devolvia as fontes na ordem em que o payload as listou, e a
    consulta na ordem do banco. Quem exibisse o artefato veria as fontes
    trocarem de lugar conforme a rota de onde vieram.
    """

    demand_id, source_ids = demand_with_sources
    # Enviadas em ordem decrescente de identificador de proposito: e a ordem que
    # o banco nao usa, entao o teste falha se a resposta ecoar o payload.
    ao_contrario = sorted(source_ids, key=str, reverse=True)

    criado = api.post(
        f"/api/v1/demands/{demand_id}/artifacts",
        json=artifact_payload(ao_contrario),
    ).json()
    consultado = api.get(f"/api/v1/demands/{demand_id}/artifacts").json()[0]

    da_criacao = [fonte["id"] for fonte in criado["sources"]]
    da_consulta = [fonte["id"] for fonte in consultado["sources"]]

    assert da_criacao == da_consulta
    assert da_criacao == sorted(da_criacao)


def test_ai_version_cannot_exist_without_the_raw_output(
    engine: Engine, demand_with_sources: tuple[UUID, list[UUID]]
) -> None:
    """Versao da IA sem o bruto nao e rastreavel: nao da para dizer o que gerou o quê."""

    demand_id, _ = demand_with_sources
    with Session(engine) as session:
        artifact = Artifact(demand_id=demand_id, type="REQUISITOS_EXTRAIDOS", title="Sem bruto")
        session.add(artifact)
        session.flush()
        session.add(
            ArtifactVersion(
                artifact_id=artifact.id,
                number=1,
                raw_content=None,
                content={"tema": "Dados"},
                origin="IA",
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()


def test_human_version_may_have_no_raw_output(
    engine: Engine, demand_with_sources: tuple[UUID, list[UUID]]
) -> None:
    """Quem edita na revisao (RF14) nao produz saida de modelo; gravar "" seria mentira."""

    demand_id, _ = demand_with_sources
    with Session(engine) as session:
        author = session.scalars(sa.select(User)).one()
        artifact = Artifact(demand_id=demand_id, type="REQUISITOS_EXTRAIDOS", title="Revisado")
        session.add(artifact)
        session.flush()
        session.add(
            ArtifactVersion(
                artifact_id=artifact.id,
                number=1,
                raw_content=None,
                content={"tema": "Dados revisados"},
                origin="HUMANO",
                author_id=author.id,
            )
        )
        session.commit()

        gravada = session.scalars(
            sa.select(ArtifactVersion).where(ArtifactVersion.origin == "HUMANO")
        ).one()
        assert gravada.raw_content is None
