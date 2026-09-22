"""Aceite RF05: o andamento de tudo numa consulta so, agrupado por etapa.

O quadro tem colunas fixas, entao o teste cobre as duas coisas que a interface
nao consegue inventar sozinha: que as cinco etapas voltam sempre, e que o
``total`` de cada coluna conta todas as demandas do filtro, nao so as que
couberam no recorte.
"""

from datetime import UTC, datetime
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.domain.enums import PipelineStage
from app.models import Client, Demand, User

ETAPAS = [etapa.value for etapa in PipelineStage]


@pytest.fixture
def board_catalog(engine: Engine) -> dict[str, UUID]:
    """Demandas espalhadas pelas etapas, com dois clientes e dois responsaveis."""

    with Session(engine) as session:
        cliente_a = Client(name="Industria Alfa")
        cliente_b = Client(name="Industria Beta")
        dono_a = User(name="Marina", email="marina@example.com", password_hash="hash")
        dono_b = User(name="Caio", email="caio@example.com", password_hash="hash")
        session.add_all([cliente_a, cliente_b, dono_a, dono_b])
        session.flush()

        especificacoes = [
            ("NR-12", cliente_a.id, dono_a.id, "CAPTACAO", "ABERTA"),
            ("Lideranca", cliente_a.id, dono_a.id, "CAPTACAO", "ABERTA"),
            ("Excel", cliente_b.id, dono_b.id, "CAPTACAO", "GANHA"),
            ("Dados", cliente_a.id, None, "ESTRUTURACAO", "ABERTA"),
            ("Seguranca", cliente_b.id, dono_a.id, "PROPOSTA", "ABERTA"),
        ]
        for titulo, client_id, owner_id, etapa, situacao in especificacoes:
            session.add(
                Demand(
                    client_id=client_id,
                    title=titulo,
                    owner_id=owner_id,
                    current_stage=etapa,
                    status=situacao,
                )
            )
        session.commit()
        return {
            "cliente_a": cliente_a.id,
            "cliente_b": cliente_b.id,
            "dono_a": dono_a.id,
            "dono_b": dono_b.id,
        }


def quadro(api: TestClient, **filtros):
    resposta = api.get("/api/v1/pipeline", params=filtros)
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


def por_etapa(corpo) -> dict[str, dict]:
    return {grupo["stage"]: grupo for grupo in corpo["stages"]}


def test_every_stage_comes_back_even_when_empty(api: TestClient, board_catalog) -> None:
    """A coluna vazia faz parte do quadro; omiti-la deixaria a interface adivinhar."""

    corpo = quadro(api)

    assert [grupo["stage"] for grupo in corpo["stages"]] == ETAPAS
    grupos = por_etapa(corpo)
    assert grupos["PRODUTO"]["total"] == 0
    assert grupos["PRODUTO"]["items"] == []


def test_demands_land_in_their_current_stage(api: TestClient, board_catalog) -> None:
    grupos = por_etapa(quadro(api))

    assert grupos["CAPTACAO"]["total"] == 3
    assert grupos["ESTRUTURACAO"]["total"] == 1
    assert grupos["PROPOSTA"]["total"] == 1
    assert grupos["ACOMPANHAMENTO"]["total"] == 0


def test_each_card_carries_what_the_column_shows(api: TestClient, board_catalog) -> None:
    """Cliente, titulo, responsavel e situacao: o minimo do cartao (RF05)."""

    grupos = por_etapa(quadro(api))
    cartao = next(item for item in grupos["ESTRUTURACAO"]["items"] if item["title"] == "Dados")

    assert cartao["client"]["name"] == "Industria Alfa"
    assert cartao["status"] == "ABERTA"
    assert cartao["owner"] is None


def test_owner_comes_with_the_name_not_only_the_identifier(api: TestClient, board_catalog) -> None:
    """O cartao mostra o nome; devolver so o UUID obrigaria a uma consulta por cartao."""

    grupos = por_etapa(quadro(api))
    cartao = next(item for item in grupos["PROPOSTA"]["items"] if item["title"] == "Seguranca")

    assert cartao["owner"]["name"] == "Marina"
    assert cartao["client"]["name"] == "Industria Beta"


def test_total_counts_the_whole_stage_not_only_the_page(api: TestClient, board_catalog) -> None:
    """O cabecalho da coluna precisa do numero real, mesmo com o recorte menor."""

    grupos = por_etapa(quadro(api, limit=1))

    assert grupos["CAPTACAO"]["total"] == 3
    assert len(grupos["CAPTACAO"]["items"]) == 1


def test_client_filter_applies_to_every_stage(api: TestClient, board_catalog) -> None:
    grupos = por_etapa(quadro(api, client_id=str(board_catalog["cliente_b"])))

    assert grupos["CAPTACAO"]["total"] == 1
    assert grupos["ESTRUTURACAO"]["total"] == 0
    assert grupos["PROPOSTA"]["total"] == 1


def test_owner_filter_applies_to_every_stage(api: TestClient, board_catalog) -> None:
    grupos = por_etapa(quadro(api, owner_id=str(board_catalog["dono_a"])))

    assert grupos["CAPTACAO"]["total"] == 2
    assert grupos["PROPOSTA"]["total"] == 1
    assert grupos["ESTRUTURACAO"]["total"] == 0


def test_status_filter_applies_to_every_stage(api: TestClient, board_catalog) -> None:
    grupos = por_etapa(quadro(api, status="GANHA"))

    assert grupos["CAPTACAO"]["total"] == 1
    assert grupos["ESTRUTURACAO"]["total"] == 0


def test_filters_combine_with_and(api: TestClient, board_catalog) -> None:
    grupos = por_etapa(
        quadro(
            api, client_id=str(board_catalog["cliente_a"]), owner_id=str(board_catalog["dono_a"])
        )
    )

    assert grupos["CAPTACAO"]["total"] == 2
    assert grupos["ESTRUTURACAO"]["total"] == 0


def test_board_total_is_the_sum_of_the_columns(api: TestClient, board_catalog) -> None:
    corpo = quadro(api)

    assert corpo["total"] == sum(grupo["total"] for grupo in corpo["stages"])
    assert corpo["total"] == 5


def test_period_without_timezone_is_refused(api: TestClient, board_catalog) -> None:
    """Mesma recusa da listagem (RF03): os dois caminhos compartilham a validacao."""

    resposta = api.get("/api/v1/pipeline", params={"from": "2026-01-01T00:00:00"})

    assert resposta.status_code == 422
    assert resposta.json()["error"]["details"]["issues"][0]["location"] == ["query", "from"]


def test_inverted_period_is_refused(api: TestClient, board_catalog) -> None:
    resposta = api.get(
        "/api/v1/pipeline",
        params={"from": "2026-06-01T00:00:00+00:00", "to": "2026-01-01T00:00:00+00:00"},
    )

    assert resposta.status_code == 422


def test_period_filter_narrows_the_board(api: TestClient, engine: Engine, board_catalog) -> None:
    with Session(engine) as session:
        antiga = session.query(Demand).filter(Demand.title == "NR-12").one()
        antiga.created_at = datetime(2020, 1, 1, tzinfo=UTC)
        session.commit()

    grupos = por_etapa(quadro(api, **{"from": "2026-01-01T00:00:00+00:00"}))

    assert grupos["CAPTACAO"]["total"] == 2


def test_stage_is_not_a_filter_here(api: TestClient, board_catalog) -> None:
    """Filtrar por etapa num agrupamento por etapa nao faz sentido e e recusado."""

    assert api.get("/api/v1/pipeline", params={"stage": "CAPTACAO"}).status_code == 422


def test_limit_above_the_ceiling_is_refused(api: TestClient, board_catalog) -> None:
    assert api.get("/api/v1/pipeline", params={"limit": 101}).status_code == 422


def test_board_without_demands_still_has_five_columns(api: TestClient) -> None:
    corpo = quadro(api)

    assert [grupo["stage"] for grupo in corpo["stages"]] == ETAPAS
    assert corpo["total"] == 0
