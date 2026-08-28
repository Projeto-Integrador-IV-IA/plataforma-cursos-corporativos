"""Modelo ORM: empresa cliente (RF01).

Tabela ``clients``. Campos previstos: id (UUID), nome corporativo, CNPJ
(opcional), segmento/nicho, contato principal, observacoes, timestamps de
criacao e atualizacao, autor da criacao.

Relacionamento: 1:N com ``demands``, com integridade referencial garantida no
banco (RNF08). Cliente com demandas nao pode ser removido fisicamente.

Implementacao da entidade persistida de cliente.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    nome: Mapped[str] = mapped_column(Text, nullable=False)
    cnpj: Mapped[str | None] = mapped_column(Text, unique=True)
    segmento: Mapped[str | None] = mapped_column(Text)
    contato_nome: Mapped[str | None] = mapped_column(Text)
    contato_email: Mapped[str | None] = mapped_column(Text)
    contato_telefone: Mapped[str | None] = mapped_column(Text)
    observacoes: Mapped[str | None] = mapped_column(Text)
    ativo: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
