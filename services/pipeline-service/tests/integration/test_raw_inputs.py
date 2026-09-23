"""Aceite RF09: a fonte bruta e confirmada no banco e volta inteira na consulta.

O requisito nao e "aceitar o texto", e sim **nao perde-lo** (RNF05, RNF09). Por
isso os testes verificam as duas pontas: que a gravacao acontece em transacao
propria, antes de qualquer processamento, e que o conteudo original e
recuperavel byte a byte depois - persistir sem caminho de leitura nao provaria
nada.
"""

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
    """Varias fontes na mesma demanda: nenhuma se sobrepoe a outra.

    Este teste afirma **completude**, nao ordem. A tabela nao tem coluna de
    ordem de recebimento, e ``created_at`` nao serve como uma: o
    ``CURRENT_TIMESTAMP`` do SQLite tem resolucao de segundo, entao fontes
    captadas no mesmo segundo empatam e o desempate cai no ``id``, que e
    aleatorio. Garantir a ordem de chegada e o RF10 (card #32), que precisa
    acrescentar a coluna - ate la, prometer ordem aqui seria mentira verificada
    por um teste verde no Postgres e vermelho no banco da CI.
    """

    for indice, origem in enumerate(("EMAIL", "MENSAGENS", "TRANSCRICAO")):
        captar(api, demand, operator, content=f"fonte {indice}", source=origem)

    fontes = api.get(f"/api/v1/demands/{demand}").json()["raw_inputs"]

    assert len(fontes) == 3
    assert {f["original_content"] for f in fontes} == {"fonte 0", "fonte 1", "fonte 2"}
    assert {f["source"] for f in fontes} == {"EMAIL", "MENSAGENS", "TRANSCRICAO"}


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
