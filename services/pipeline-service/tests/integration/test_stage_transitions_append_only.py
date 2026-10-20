"""A trilha de etapas nao tem caminho de alteracao: nem pelo ORM, nem pelo banco (RNF09).

Duas camadas, testadas separadas: o modelo recusa ``UPDATE`` e ``DELETE`` pelo
ORM com erro claro; o banco recusa qualquer um dos dois, inclusive os em massa
que o ORM nao intercepta, por gatilho da migration ``20261020_1200``.
"""

from uuid import UUID

import pytest
import sqlalchemy as sa
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.stage_transition import AppendOnlyViolationError, StageTransition

from ._schema import (
    DEMAND_ID,
    USER_ID,
    assert_rejected,
    insert_client,
    insert_demand,
    insert_user,
)

TRANSITION_ID = "0000000000000000000000000000000a"


@pytest.fixture
def recorded(engine: Engine) -> str:
    """Uma transicao ja gravada, com demanda, cliente e usuario por tras."""

    with engine.connect() as connection:
        insert_user(connection)
        insert_client(connection)
        insert_demand(connection)
        connection.execute(
            sa.text(
                """
                INSERT INTO stage_transitions (id, demand_id, from_stage, to_stage, author_id)
                VALUES (:id, :demand_id, 'CAPTACAO', 'ESTRUTURACAO', :author_id)
                """
            ),
            {"id": TRANSITION_ID, "demand_id": DEMAND_ID, "author_id": USER_ID},
        )
        connection.commit()
    return TRANSITION_ID


def _trail(engine: Engine) -> list[tuple[str, str | None]]:
    with engine.connect() as connection:
        rows = connection.execute(sa.text("SELECT id, reason FROM stage_transitions")).all()
        return [(row[0], row[1]) for row in rows]


def test_database_refuses_update(engine: Engine, recorded: str) -> None:
    with engine.connect() as connection:
        assert_rejected(
            connection,
            "UPDATE stage_transitions SET reason = 'adulterado' WHERE id = :id",
            {"id": recorded},
        )

    assert _trail(engine) == [(recorded, None)]


def test_database_refuses_delete(engine: Engine, recorded: str) -> None:
    with engine.connect() as connection:
        assert_rejected(
            connection, "DELETE FROM stage_transitions WHERE id = :id", {"id": recorded}
        )

    assert _trail(engine) == [(recorded, None)]


def test_database_refuses_mass_update_and_delete(engine: Engine, recorded: str) -> None:
    with engine.connect() as connection:
        assert_rejected(connection, "UPDATE stage_transitions SET reason = 'x'", {})
        assert_rejected(connection, "DELETE FROM stage_transitions", {})

    assert _trail(engine) == [(recorded, None)]


def test_database_still_accepts_new_events(engine: Engine, recorded: str) -> None:
    with engine.connect() as connection:
        connection.execute(
            sa.text(
                """
                INSERT INTO stage_transitions (id, demand_id, from_stage, to_stage, author_id)
                VALUES ('0000000000000000000000000000000b', :demand_id,
                        'ESTRUTURACAO', 'PRODUTO', :author_id)
                """
            ),
            {"demand_id": DEMAND_ID, "author_id": USER_ID},
        )
        connection.commit()

    assert len(_trail(engine)) == 2


def test_orm_refuses_to_change_an_event(engine: Engine, recorded: str) -> None:
    with Session(engine) as session:
        transition = session.get(StageTransition, UUID(recorded))
        assert transition is not None

        transition.reason = "adulterado"
        with pytest.raises(AppendOnlyViolationError):
            session.flush()
        session.rollback()

    assert _trail(engine) == [(recorded, None)]


def test_orm_refuses_to_delete_an_event(engine: Engine, recorded: str) -> None:
    with Session(engine) as session:
        transition = session.get(StageTransition, UUID(recorded))
        assert transition is not None

        session.delete(transition)
        with pytest.raises(AppendOnlyViolationError):
            session.flush()
        session.rollback()

    assert _trail(engine) == [(recorded, None)]


def test_orm_bulk_statements_are_stopped_by_the_database(engine: Engine, recorded: str) -> None:
    """O ORM nao dispara ``before_update`` em UPDATE/DELETE em massa; o gatilho pega."""

    with Session(engine) as session:
        with pytest.raises(IntegrityError):
            session.execute(sa.update(StageTransition).values(reason="adulterado"))
        session.rollback()

        with pytest.raises(IntegrityError):
            session.execute(sa.delete(StageTransition))
        session.rollback()

    assert _trail(engine) == [(recorded, None)]
