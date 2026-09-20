"""Dominio da captacao multicanal de texto bruto (RF09)."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class SourceKind(StrEnum):
    """Origens aceitas, alinhadas ao vocabulario persistido pelo pipeline."""

    EMAIL = "EMAIL"
    TRANSCRICAO = "TRANSCRICAO"
    MENSAGENS = "MENSAGENS"
    ANOTACAO = "ANOTACAO"
    OUTRO = "OUTRO"


@dataclass(frozen=True, slots=True)
class RawDemand:
    """Conteudo imutavel exatamente como recebido do operador."""

    demand_id: UUID
    text: str
    source_type: SourceKind

    def __post_init__(self) -> None:
        if not self.text.strip():
            raise ValueError("text must not be blank")


@dataclass(frozen=True, slots=True)
class PersistedRawDemand:
    """Confirmacao de que o pipeline concluiu a transacao do texto bruto."""

    raw_input_id: UUID
    demand_id: UUID
    source_type: SourceKind
    created_at: datetime
