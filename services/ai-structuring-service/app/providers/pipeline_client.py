"""Cliente HTTP para o pipeline-service (RF13).

Mesmo nao sendo um provedor de LLM, este módulo fala com outro processo pela
rede e por isso vive aqui: a regra de isolamento (RNF03, ADR-0006, ver
``tests/unit/test_provider_isolation.py``) mantém todo cliente HTTP dentro de
``app/providers``, para que o restante do serviço nunca precise importar um
SDK ou biblioteca de transporte.
"""

from uuid import UUID

import httpx


async def publicar_artefato(
    pipeline_service_url: str,
    demand_id: UUID,
    payload: dict,
    *,
    timeout_seconds: float = 15.0,
) -> None:
    """Envia o artefato gerado pela IA para o pipeline-service anexar a demanda.

    Args:
        pipeline_service_url: base da API do pipeline-service, sem barra final.
        demand_id: identificador da demanda que recebe o artefato.
        payload: corpo ja montado no formato esperado pelo endpoint de artefatos.
        timeout_seconds: tempo maximo da chamada (RNF06).

    Raises:
        httpx.HTTPError: falha de transporte ou resposta de erro do pipeline-service.
    """

    url = f"{pipeline_service_url}/api/v1/demands/{demand_id}/artifacts"
    async with httpx.AsyncClient(timeout=timeout_seconds) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
