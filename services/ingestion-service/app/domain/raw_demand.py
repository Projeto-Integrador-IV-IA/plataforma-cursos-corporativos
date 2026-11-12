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
class SourceSegment:
    """Trecho citavel com faixa recuperavel no texto bruto original."""

    id: UUID
    source_id: UUID
    position: int
    text: str
    original_start_offset: int
    original_end_offset: int

    def __post_init__(self) -> None:
        if self.position < 1:
            raise ValueError("position must start at 1")
        if not self.text.strip():
            raise ValueError("text must not be blank")
        if self.original_start_offset < 0:
            raise ValueError("original_start_offset must not be negative")
        if self.original_end_offset <= self.original_start_offset:
            raise ValueError("original_end_offset must be after original_start_offset")


@dataclass(frozen=True, slots=True)
class RawDemand:
    """Conteudo imutavel exatamente como recebido do operador."""

    demand_id: UUID
    text: str
    source_type: SourceKind
    previous_attempt_id: UUID | None = None

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
    previous_attempt_id: UUID | None = None
