"""Backfill e integridade da ordem de recebimento (RF10)."""

from uuid import UUID, uuid4

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError

from .test_raw_inputs import demand as demand
from .test_raw_inputs import operator as operator


def test_upgrade_numbers_legacy_sources_and_downgrade_preserves_content(
    engine: Engine, demand: UUID, operator: UUID
) -> None:
    config = Config("alembic.ini")
    command.downgrade(config, "20260920_1200")
    with engine.begin() as connection:
        for index, date in [(3, "2026-10-25"), (2, "2026-10-24"), (1, "2026-10-24")]:
            connection.execute(
                sa.text("""
                    INSERT INTO raw_inputs
                        (id, demand_id, author_id, original_content, normalized_content,
                         source, created_at)
                    VALUES (:id, :demand, :author, :original, 'Copia', 'EMAIL', :date)
                """),
                dict(
                    id=UUID(int=index).hex,
                    demand=demand.hex,
                    author=operator.hex,
                    original=f"  Original {index}\r\n",
                    date=date,
                ),
            )
    command.upgrade(config, "head")
    with engine.connect() as connection:
        rows = connection.execute(
            sa.text(
                "SELECT received_order, original_content, normalized_content "
                "FROM raw_inputs ORDER BY received_order"
            )
        ).all()
        assert rows == [(i, f"  Original {i}\r\n", "Copia") for i in (1, 2, 3)]
    command.downgrade(config, "20260920_1200")
    with engine.connect() as connection:
        assert "received_order" not in {
            c["name"] for c in sa.inspect(connection).get_columns("raw_inputs")
        }
        assert connection.scalar(sa.text("SELECT COUNT(*) FROM raw_inputs")) == 3
        assert (
            connection.scalar(
                sa.text("SELECT original_content FROM raw_inputs ORDER BY id LIMIT 1")
            )
            == "  Original 1\r\n"
        )
    command.upgrade(config, "head")


@pytest.mark.parametrize("position", [0, -1, None, 1])
def test_database_rejects_invalid_or_duplicate_order(
    engine: Engine, demand: UUID, operator: UUID, position: int | None
) -> None:
    statement = sa.text("""
        INSERT INTO raw_inputs
            (id, demand_id, author_id, original_content, source, received_order)
        VALUES (:id, :demand, :author, 'Original', 'EMAIL', :position)
    """)
    with engine.begin() as connection:
        connection.execute(
            statement, dict(id=uuid4().hex, demand=demand.hex, author=operator.hex, position=1)
        )
    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(
            statement,
            dict(id=uuid4().hex, demand=demand.hex, author=operator.hex, position=position),
        )
