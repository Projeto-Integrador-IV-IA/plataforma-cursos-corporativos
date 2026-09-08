"""Tipos SQL compartilhados pelos modelos relacionais."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

UUID_TYPE = sa.Uuid().with_variant(postgresql.UUID(as_uuid=True), "postgresql")
JSON_TYPE = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")
