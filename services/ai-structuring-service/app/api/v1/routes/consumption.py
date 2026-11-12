"""Rota de consulta do consumo agregado de tokens (RNF22).

    GET /api/v1/consumption     consumo do dia civil (UTC), por padrao hoje

Rota fina, no mesmo estilo de ``structuring.py``: so traduz o acumulado de
``app.core.consumption`` e o teto do ambiente para o DTO da resposta - nenhuma
regra de negocio mora aqui.
"""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.config import Settings, get_settings
from app.core.consumption import consultar_consumo
from app.schemas.consumption import ConsumptionRead

router = APIRouter(tags=["consumption"])


@router.get(
    "/consumption",
    response_model=ConsumptionRead,
    summary="Consultar o consumo de tokens acumulado em um dia",
    response_description="Chamadas e tokens do dia, e se o teto configurado foi ultrapassado.",
)
async def get_consumption(
    settings: Annotated[Settings, Depends(get_settings)],
    date_: Annotated[
        date | None,
        Query(
            alias="date",
            description="Dia civil (UTC) a consultar, no formato AAAA-MM-DD. "
            "Hoje (UTC), quando omitido.",
        ),
    ] = None,
) -> ConsumptionRead:
    """Devolve o consumo acumulado do dia, sem exigir que tenha havido chamada.

    Dia sem nenhuma chamada registrada no processo devolve consumo zerado, nao
    404: "ainda nao houve chamada" e uma resposta valida, nao um erro.
    """

    consumo = consultar_consumo(date_)
    return ConsumptionRead.from_consumo(consumo, daily_limit=settings.llm_daily_token_budget)
