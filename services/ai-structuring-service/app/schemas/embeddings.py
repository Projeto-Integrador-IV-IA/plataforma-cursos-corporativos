"""DTOs da rota de embeddagem de trechos (card #160, RF29)."""

from pydantic import BaseModel, ConfigDict, Field

from app.services.embedding_service import EmbeddingRunResult


class EmbeddingRunRead(BaseModel):
    """Desfecho de uma rodada de embeddagem, devolvido ao chamador."""

    model_config = ConfigDict(frozen=True)

    demand_id: str
    model: str = Field(description="Modelo de embedding usado nesta rodada (RNF08).")
    segments_embedded: int = Field(
        description="Trechos processados. Zero quando a demanda nao tem trecho persistido."
    )

    @classmethod
    def from_result(cls, resultado: EmbeddingRunResult) -> "EmbeddingRunRead":
        return cls(
            demand_id=resultado.demand_id,
            model=resultado.model,
            segments_embedded=resultado.segments_embedded,
        )
