"""Base declarativa do SQLAlchemy e registro de modelos.

Importa todos os modelos de ``app.models`` para que o Alembic enxergue o
metadata completo ao gerar migrations automaticamente.

TODO(scaffolding): definir ``Base`` e importar os modelos.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
