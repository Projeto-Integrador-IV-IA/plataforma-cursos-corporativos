"""DTO de consulta do consumo agregado de tokens (RNF22)."""

from datetime import date
from typing import Any, Final, Self

from pydantic import BaseModel, ConfigDict

from app.core.consumption import ConsumoDoDia

#: Resposta de exemplo exibida no Swagger.
EXEMPLO_DE_RESPOSTA: Final[dict[str, Any]] = {
    "date": "2026-11-12",
    "calls": 7,
    "prompt_tokens": 9821,
    "completion_tokens": 2114,
    "total_tokens": 11935,
    "daily_limit": 200_000,
    "limit_exceeded": False,
}


class ConsumptionRead(BaseModel):
    """Consumo de tokens acumulado em um dia civil (UTC) (RNF22).

    Attributes:
        date: dia civil (UTC) a que o consumo se refere.
        calls: chamadas bem-sucedidas ao provedor contabilizadas no dia.
        prompt_tokens: tokens de entrada somados das chamadas do dia.
        completion_tokens: tokens de saida somados das chamadas do dia.
        total_tokens: soma dos dois - o numero que o limite diario vigia.
        daily_limit: teto configurado em ``LLM_DAILY_TOKEN_BUDGET``; ``None``
            quando o ambiente nao define limite (sem alerta ligado).
        limit_exceeded: se ``total_tokens`` ja passou ``daily_limit`` hoje.
            Sempre ``False`` quando ``daily_limit`` e ``None``.
    """

    model_config = ConfigDict(
        frozen=True,
        json_schema_extra={"examples": [EXEMPLO_DE_RESPOSTA]},
    )

    date: date
    calls: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    daily_limit: int | None
    limit_exceeded: bool

    @classmethod
    def from_consumo(cls, consumo: ConsumoDoDia, *, daily_limit: int | None) -> Self:
        """Monta a resposta a partir do acumulado do dia e do teto configurado."""

        return cls(
            date=consumo.dia,
            calls=consumo.chamadas,
            prompt_tokens=consumo.tokens_entrada,
            completion_tokens=consumo.tokens_saida,
            total_tokens=consumo.tokens_totais,
            daily_limit=daily_limit,
            limit_exceeded=daily_limit is not None and consumo.tokens_totais > daily_limit,
        )
