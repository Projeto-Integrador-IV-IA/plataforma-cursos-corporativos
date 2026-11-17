"""Cliente HTTP do pipeline-service: anexa o resultado da estruturacao a demanda (RF13).

Fica fora de ``app/providers/`` de proposito. A restricao de ``app/providers/``
(RNF03, ver ``tests/unit/test_provider_isolation.py``) existe para que troca de
FORNECEDOR de LLM seja configuracao, nunca refatoracao - falar com outro
microsservico nosso e uma dependencia de infraestrutura diferente, sem esse
risco, e por isso ``app/clients/`` tem sua propria isencao na mesma guarda de
arquitetura.
"""

from typing import Any

import httpx


class PipelineServiceClient:
    """Envia o artefato gerado pela IA ao pipeline-service, dono do banco (ADR-0001)."""

    def __init__(self, base_url: str, *, timeout_seconds: float = 15.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds

    async def persist_artifact(self, demand_id: str, payload: dict[str, Any]) -> None:
        """Cria o artefato da demanda com o corpo ja montado pelo chamador.

        Levanta ``httpx.HTTPError`` em qualquer falha de rede ou resposta sem
        sucesso; quem chama decide como isso afeta o desfecho da execucao.
        """

        url = f"{self._base_url}/api/v1/demands/{demand_id}/artifacts"
        async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
