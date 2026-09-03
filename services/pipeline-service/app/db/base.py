"""Base declarativa compartilhada pelos modelos do pipeline-service."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Agrupa o metadata usado pelos modelos e pelo Alembic."""
