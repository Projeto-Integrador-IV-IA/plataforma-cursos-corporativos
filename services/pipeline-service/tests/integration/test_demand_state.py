"""Estado da demanda no pipeline, garantido pelo banco (RF05).

A etapa inicial nao depende da aplicacao: quem insere uma demanda sem informar
``current_stage`` recebe ``CAPTACAO`` do proprio schema.
"""

import sqlalchemy as sa
from sqlalchemy.engine import Connection

from app.domain.enums import DemandStatus, PipelineStage

from ._schema import DEMAND_ID, insert_client, insert_demand


def test_new_demand_starts_in_captacao(database: Connection) -> None:
    insert_client(database)
    insert_demand(database)

    current_stage = database.scalar(
        sa.text("SELECT current_stage FROM demands WHERE id = :id"),
        {"id": DEMAND_ID},
    )

    assert current_stage == PipelineStage.CAPTACAO.value


def test_new_demand_starts_open(database: Connection) -> None:
    insert_client(database)
    insert_demand(database)

    status = database.scalar(
        sa.text("SELECT status FROM demands WHERE id = :id"),
        {"id": DEMAND_ID},
    )

    assert status == DemandStatus.ABERTA.value
