"""Audio validado para persistencia integral, antes da transcricao (RF30)."""

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class AudioSource:
    demand_id: UUID
    filename: str
    content_type: str
    content: bytes
    duration_seconds: float
    sha256: str
