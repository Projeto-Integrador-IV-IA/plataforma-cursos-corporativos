"""Chamada ao `pipeline-service` para anexar o resultado da IA a demanda (RF13)."""

from typing import Any

import httpx


async def create_artifact(
    pipeline_service_url: str,
    demand_id: str,
    payload: dict[str, Any],
) -> None:
    """Envia o artefato gerado para `POST /api/v1/demands/{demand_id}/artifacts`.

    Repassa qualquer erro HTTP do pipeline-service (`raise_for_status`); quem
    chama decide o que fazer com a falha.
    """

    url = f"{pipeline_service_url}/api/v1/demands/{demand_id}/artifacts"
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
