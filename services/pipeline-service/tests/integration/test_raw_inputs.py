"""Aceite RF09: a fonte bruta e confirmada no banco e volta inteira na consulta.

O requisito nao e "aceitar o texto", e sim **nao perde-lo** (RNF05, RNF09). Por
isso os testes verificam as duas pontas: que a gravacao acontece em transacao
propria, antes de qualquer processamento, e que o conteudo original e
recuperavel byte a byte depois - persistir sem caminho de leitura nao provaria
nada.
"""

from datetime import datetime
from unittest.mock import patch
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.models import Demand, RawInput, User

TEXTO_DE_WHATSAPP = (
    "Boa tarde! Precisamos treinar 25 tecnicos na NR-12 ate marco.\n"
    "Pode ser presencial na planta 2. Qualquer coisa me chama aqui. []'s, Marina"
)


@pytest.fixture
def operator(engine: Engine) -> UUID:
    with Session(engine) as session:
        user = User(name="Operadora", email="operadora@example.com", password_hash="hash")
        session.add(user)
        session.commit()
        return user.id


@pytest.fixture
def demand(engine: Engine, company: UUID) -> UUID:
    with Session(engine) as session:
        demand = Demand(client_id=company, title="Treinamento de NR-12")
        session.add(demand)
        session.commit()
        return demand.id


def captar(
    api: TestClient,
    demand_id: UUID,
    author_id: UUID,
    *,
    content: str = TEXTO_DE_WHATSAPP,
    source: str = "MENSAGENS",
):
    return api.post(
        f"/api/v1/demands/{demand_id}/raw-inputs",
        json={"original_content": content, "source": source},
        headers={"X-User-ID": str(author_id)},
    )


def test_raw_input_is_persisted_with_the_original_text(
    api: TestClient, demand: UUID, operator: UUID
) -> None:
    resposta = captar(api, demand, operator)

    assert resposta.status_code == 201, resposta.text
    corpo = resposta.json()
    assert corpo["original_content"] == TEXTO_DE_WHATSAPP
    assert corpo["source"] == "MENSAGENS"
    assert corpo["demand_id"] == str(demand)
    assert corpo["author_id"] == str(operator)


def test_persisted_text_survives_in_the_database_untouched(
    api: TestClient, engine: Engine, demand: UUID, operator: UUID
) -> None:
    """Nada de normalizacao na captacao: o que o operador colou e o que fica."""

    captar(api, demand, operator)

    with Session(engine) as session:
        gravado = session.query(RawInput).one()
        assert gravado.original_content == TEXTO_DE_WHATSAPP
        assert gravado.normalized_content is None
        assert gravado.truncated is False


def test_raw_input_comes_back_in_the_demand_detail(
    api: TestClient, demand: UUID, operator: UUID
) -> None:
    """Sem esta leitura o RF09 grava num lugar de onde ninguem tira (RF04)."""

    captar(api, demand, operator)

    detalhe = api.get(f"/api/v1/demands/{demand}")

    assert detalhe.status_code == 200, detalhe.text
    fontes = detalhe.json()["raw_inputs"]
    assert len(fontes) == 1
    assert fontes[0]["original_content"] == TEXTO_DE_WHATSAPP
    assert fontes[0]["source"] == "MENSAGENS"


def test_every_captured_source_comes_back(api: TestClient, demand: UUID, operator: UUID) -> None:
    """Todas as fontes voltam na ordem de recebimento (RF10, #32)."""

    for indice, origem in enumerate(("EMAIL", "MENSAGENS", "TRANSCRICAO")):
        captar(api, demand, operator, content=f"fonte {indice}", source=origem)

    fontes = api.get(f"/api/v1/demands/{demand}").json()["raw_inputs"]

    assert len(fontes) == 3
    assert {f["original_content"] for f in fontes} == {"fonte 0", "fonte 1", "fonte 2"}
    assert {f["source"] for f in fontes} == {"EMAIL", "MENSAGENS", "TRANSCRICAO"}
    assert [f["original_content"] for f in fontes] == ["fonte 0", "fonte 1", "fonte 2"]
    assert [f["received_order"] for f in fontes] == [1, 2, 3]


def test_receipt_order_survives_timestamp_ties_and_normalization(
    api: TestClient, engine: Engine, demand: UUID, operator: UUID
) -> None:
    """UUIDs em ordem inversa e datas empatadas nao invertem uma negociacao."""

    originals = ["  Primeiro: 20 pessoas.\r\n", "\tCorreção: 30 pessoas! 😀\n"]
    ids = [UUID(int=200), UUID(int=100)]
    for original, source_id in zip(originals, ids, strict=True):
        with patch("app.services.raw_input_service.RawInput", wraps=RawInput) as model:
            model.side_effect = lambda source_id=source_id, **kwargs: RawInput(
                id=source_id, **kwargs
            )
            response = captar(api, demand, operator, content=original)
        assert response.status_code == 201, response.text
    with Session(engine) as session:
        for source_id in ids:
            session.get(RawInput, source_id).created_at = datetime(2026, 10, 25, 12)
        session.commit()

    for source_id in reversed(ids):
        response = api.patch(
            f"/api/v1/raw-inputs/{source_id}/normalization",
            json={"normalized_content": "Copia sanitizada"},
        )
        assert response.status_code == 200, response.text
    sources = api.get(f"/api/v1/demands/{demand}").json()["raw_inputs"]
    assert [s["id"] for s in sources] == [str(value) for value in ids]
    assert [s["received_order"] for s in sources] == [1, 2]
    assert [s["original_content"].encode("utf-8") for s in sources] == [
        value.encode("utf-8") for value in originals
    ]
    with Session(engine) as session:
        assert all(
            session.get(RawInput, value).normalized_content == "Copia sanitizada" for value in ids
        )


def test_sequence_is_per_demand_and_rejected_capture_does_not_advance_it(
    api: TestClient, engine: Engine, demand: UUID, company: UUID, operator: UUID
) -> None:
    with Session(engine) as session:
        other = Demand(client_id=company, title="Outra negociacao")
        session.add(other)
        session.commit()
        other_id = other.id
    assert captar(api, demand, operator).json()["received_order"] == 1
    assert captar(api, demand, uuid4()).status_code == 404
    assert captar(api, other_id, operator).json()["received_order"] == 1
    assert captar(api, demand, operator).json()["received_order"] == 2


@pytest.mark.parametrize("field", ["original_content", "received_order"])
def test_normalization_cannot_overwrite_original_or_receipt_order(
    api: TestClient, demand: UUID, operator: UUID, field: str
) -> None:
    source = captar(api, demand, operator).json()
    response = api.patch(
        f"/api/v1/raw-inputs/{source['id']}/normalization",
        json={
            "normalized_content": "Sanitizado",
            field: 99 if field == "received_order" else "Outro",
        },
    )
    assert response.status_code == 422
    saved = api.get(f"/api/v1/demands/{demand}").json()["raw_inputs"][0]
    assert saved["original_content"] == TEXTO_DE_WHATSAPP
    assert saved["received_order"] == 1


def test_capture_for_unknown_demand_is_rejected(api: TestClient, operator: UUID) -> None:
    resposta = captar(api, uuid4(), operator)

    assert resposta.status_code == 404
    assert resposta.json()["error"]["code"] == "DEMAND_NOT_FOUND"


def test_capture_by_unknown_operator_is_rejected(api: TestClient, demand: UUID) -> None:
    resposta = captar(api, demand, uuid4())

    assert resposta.status_code == 404
    assert resposta.json()["error"]["code"] == "USER_NOT_FOUND"


def test_rejected_capture_leaves_no_partial_record(
    api: TestClient, engine: Engine, demand: UUID
) -> None:
    captar(api, demand, uuid4())

    with Session(engine) as session:
        assert session.query(RawInput).count() == 0


@pytest.mark.parametrize("conteudo", ["", "   ", "\n\t "])
def test_blank_content_is_rejected(
    api: TestClient, demand: UUID, operator: UUID, conteudo: str
) -> None:
    """Texto em branco nao e captacao: seria registrar uma fonte que nao existe."""

    assert captar(api, demand, operator, content=conteudo).status_code == 422


def test_unknown_source_is_rejected(api: TestClient, demand: UUID, operator: UUID) -> None:
    assert captar(api, demand, operator, source="POMBO_CORREIO").status_code == 422


def test_unexpected_field_is_rejected(api: TestClient, demand: UUID, operator: UUID) -> None:
    """``extra=forbid`` evita que a sanitizacao (RF11) entre por engano na captacao."""

    resposta = api.post(
        f"/api/v1/demands/{demand}/raw-inputs",
        json={
            "original_content": TEXTO_DE_WHATSAPP,
            "source": "MENSAGENS",
            "normalized_content": "ja sanitizado",
        },
        headers={"X-User-ID": str(operator)},
    )

    assert resposta.status_code == 422


def test_capture_without_operator_header_is_rejected(api: TestClient, demand: UUID) -> None:
    resposta = api.post(
        f"/api/v1/demands/{demand}/raw-inputs",
        json={"original_content": TEXTO_DE_WHATSAPP, "source": "MENSAGENS"},
    )

    assert resposta.status_code == 422


def test_demand_without_sources_reports_an_empty_list(api: TestClient, demand: UUID) -> None:
    """A tela distingue "sem fontes" de "campo ausente"; o contrato sempre traz a chave."""

    assert api.get(f"/api/v1/demands/{demand}").json()["raw_inputs"] == []
