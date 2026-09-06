"""Base declarativa compartilhada pelos modelos do pipeline-service.

Quando os modelos de ``app.models`` deixarem de ser stubs, importe-os aqui para
que ``Base.metadata`` reflita o schema completo - e so entao volte a apontar
``target_metadata`` para ele em ``app/db/migrations/env.py``.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Agrupa o metadata usado pelos modelos e pelo Alembic."""
