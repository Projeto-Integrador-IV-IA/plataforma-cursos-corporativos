"""Reprocessamento: nova execucao da IA vira versao nova (RF17 consolidado, card #15).

Reprocessar e rodar a estruturacao de novo - sobre o texto original ou um
revisado - e gravar o resultado como versao nova do mesmo artefato, nunca
substituindo a anterior (append-only, RF09). A persistencia desta nova
execucao e o que este card entrega; a chamada ao LLM em si e feita pelo
``ai-structuring-service`` antes de chegar aqui.
"""

from uuid import UUID, uuid4

import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.domain.enums import ArtifactOrigin, ArtifactType
from app.models import Artifact, ArtifactSource, ArtifactVersion, RawInput, User
from app.models.demand import Demand

V1 = {"tema": "Lideranca", "carga_horaria": None}
V2_REPROCESSADA = {"tema": "Lideranca para gestores", "carga_horaria": 40}


def _create_demand_with_sources(engine: Engine, client_id: UUID) -> tuple[UUID, list[UUID]]:
    with Session(engine) as session:
        author = User(name="Operador", email=f"{uuid4().hex}@example.com", password_hash="hash")
        session.add(author)
        session.flush()
        demand = Demand(client_id=client_id, title="Demanda")
        session.add(demand)
        session.flush()
        sources = [
            RawInput(
                received_order=1,
                demand_id=demand.id,
                original_content="Texto original",
                source="EMAIL",
                author_id=author.id,
            ),
            RawInput(
                received_order=2,
                demand_id=demand.id,
                original_content="Texto revisado pela revisao humana",
                source="OUTRO",
                author_id=author.id,
            ),
        ]
        session.add_all(sources)
        session.commit()
        return demand.id, [source.id for source in sources]


def _create_artifact_with_first_version(
    engine: Engine, demand_id: UUID, first_source_id: UUID
) -> UUID:
    with Session(engine) as session:
        artifact = Artifact(
            demand_id=demand_id,
            type=ArtifactType.REQUISITOS_EXTRAIDOS.value,
            title="Estruturacao inicial",
            raw_input_id=first_source_id,
        )
        session.add(artifact)
        session.flush()
        session.add(
            ArtifactVersion(
                artifact_id=artifact.id,
                number=1,
                raw_content="resposta bruta original",
                content=V1,
                origin=ArtifactOrigin.IA.value,
                ai_metadata={"model": "teste", "prompt": "extract-requirements.v6"},
            )
        )
        session.add(
            ArtifactSource(
                artifact_id=artifact.id,
                raw_input_id=first_source_id,
                demand_id=demand_id,
            )
        )
        session.commit()
        return artifact.id


def _rows(engine: Engine, artifact_id: UUID) -> list[tuple]:
    with Session(engine) as session:
        versions = session.scalars(
            sa.select(ArtifactVersion)
            .where(ArtifactVersion.artifact_id == artifact_id)
            .order_by(ArtifactVersion.number)
        ).all()
        return [(v.number, v.origin, v.content, v.raw_content, v.previous_number) for v in versions]


def _reprocess(
    api: TestClient, artifact_id: UUID, default_source_ids: list[UUID], **overrides: object
):
    payload: dict[str, object] = {
        "raw_output": '{"tema":"Lideranca para gestores","carga_horaria":40}',
        "structured_content": V2_REPROCESSADA,
        "raw_input_ids": [str(source_id) for source_id in default_source_ids],
        "ai_metadata": {"model": "teste", "prompt": "extract-requirements.v6"},
    }
    payload.update(overrides)
    return api.post(f"/api/v1/artifacts/{artifact_id}/reprocess", json=payload)


def test_reprocess_creates_a_new_ia_version_without_touching_the_previous_one(
    api: TestClient, engine: Engine, company: UUID
) -> None:
    demand_id, source_ids = _create_demand_with_sources(engine, company)
    artifact_id = _create_artifact_with_first_version(engine, demand_id, source_ids[0])
    before = _rows(engine, artifact_id)

    response = _reprocess(api, artifact_id, [source_ids[0]])

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["number"] == 2
    assert body["previous_number"] == 1
    assert body["origin"] == ArtifactOrigin.IA.value
    assert body["structured_content"] == V2_REPROCESSADA
    assert body["raw_output"] == '{"tema":"Lideranca para gestores","carga_horaria":40}'
    assert body["author_id"] is None
    assert body["restored_from_number"] is None

    after = _rows(engine, artifact_id)
    assert after[0] == before[0]  # a versao 1 nao mudou
    assert len(after) == 2


def test_reprocessing_with_a_revised_text_links_the_new_source_without_duplicating(
    api: TestClient, engine: Engine, company: UUID
) -> None:
    """Texto revisado entra como fonte nova; a fonte original nao duplica o vinculo."""

    demand_id, source_ids = _create_demand_with_sources(engine, company)
    artifact_id = _create_artifact_with_first_version(engine, demand_id, source_ids[0])

    response = _reprocess(api, artifact_id, source_ids)  # original + revisada

    assert response.status_code == 201, response.text
    with Session(engine) as session:
        links = session.scalars(
            sa.select(ArtifactSource).where(ArtifactSource.artifact_id == artifact_id)
        ).all()
        assert {link.raw_input_id for link in links} == set(source_ids)
        assert len(links) == 2  # original (ja vinculada) + revisada (nova); sem duplicar


def test_reprocessing_twice_keeps_every_version_queryable(
    api: TestClient, engine: Engine, company: UUID
) -> None:
    demand_id, source_ids = _create_demand_with_sources(engine, company)
    artifact_id = _create_artifact_with_first_version(engine, demand_id, source_ids[0])

    _reprocess(api, artifact_id, [source_ids[0]])
    terceira = _reprocess(
        api,
        artifact_id,
        [source_ids[0]],
        structured_content={"tema": "Lideranca", "carga_horaria": 24},
        raw_output="terceira resposta",
    )

    assert terceira.status_code == 201
    assert terceira.json()["number"] == 3
    assert terceira.json()["previous_number"] == 2

    listed = api.get(f"/api/v1/artifacts/{artifact_id}/versions").json()
    assert [v["number"] for v in listed] == [1, 2, 3]


def test_reprocess_rejects_source_from_another_demand(
    api: TestClient, engine: Engine, company: UUID
) -> None:
    demand_id, source_ids = _create_demand_with_sources(engine, company)
    artifact_id = _create_artifact_with_first_version(engine, demand_id, source_ids[0])
    with Session(engine) as session:
        author = session.scalars(sa.select(User)).first()
        other_demand = Demand(client_id=company, title="Outra demanda")
        session.add(other_demand)
        session.flush()
        foreign_source = RawInput(
            received_order=1,
            demand_id=other_demand.id,
            original_content="Fonte de outra demanda",
            source="EMAIL",
            author_id=author.id,
        )
        session.add(foreign_source)
        session.commit()
        foreign_source_id = foreign_source.id

    response = _reprocess(api, artifact_id, [foreign_source_id])

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ARTIFACT_SOURCE_DEMAND_MISMATCH"
    assert len(_rows(engine, artifact_id)) == 1


def test_reprocess_rejects_unknown_source(api: TestClient, engine: Engine, company: UUID) -> None:
    demand_id, source_ids = _create_demand_with_sources(engine, company)
    artifact_id = _create_artifact_with_first_version(engine, demand_id, source_ids[0])

    response = _reprocess(api, artifact_id, [uuid4()])

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "RAW_INPUT_NOT_FOUND"
    assert len(_rows(engine, artifact_id)) == 1


def test_reprocess_unknown_artifact_is_not_found(
    api: TestClient, engine: Engine, company: UUID
) -> None:
    _demand_id, source_ids = _create_demand_with_sources(engine, company)

    response = _reprocess(api, uuid4(), [source_ids[0]])

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "ARTIFACT_NOT_FOUND"


@pytest.mark.parametrize(
    "overrides",
    [
        {"raw_output": ""},
        {"raw_input_ids": []},
        {"raw_input_ids": "repeat"},
    ],
)
def test_reprocess_validates_input(
    api: TestClient, engine: Engine, company: UUID, overrides: dict[str, object]
) -> None:
    demand_id, source_ids = _create_demand_with_sources(engine, company)
    artifact_id = _create_artifact_with_first_version(engine, demand_id, source_ids[0])
    if overrides.get("raw_input_ids") == "repeat":
        overrides = {"raw_input_ids": [str(source_ids[0]), str(source_ids[0])]}

    response = _reprocess(api, artifact_id, [source_ids[0]], **overrides)

    assert response.status_code == 422
    assert len(_rows(engine, artifact_id)) == 1


def test_swagger_documents_reprocess(api: TestClient) -> None:
    document = api.get("/openapi.json").json()
    operations = document["paths"]["/api/v1/artifacts/{artifact_id}/reprocess"]
    assert "post" in operations
    assert {"201", "404", "409", "422"} <= set(operations["post"]["responses"])
