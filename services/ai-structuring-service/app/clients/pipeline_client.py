"""Cliente HTTP do pipeline-service: anexa resultado e embeddings a demanda (RF13, RF29).

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
    """Fala com o pipeline-service, dono do banco (ADR-0001): artefato e embeddings."""

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

    async def find_artifact_id(self, demand_id: str, artifact_type: str) -> str | None:
        """Procura um artefato do tipo informado ja existente para a demanda.

        Decide entre criar (primeira execucao) e reprocessar (RF17 consolidado,
        card #15): sem essa consulta, toda execucao de IA repetida para a mesma
        demanda criaria um artefato irmao em vez de uma versao nova do mesmo
        artefato, quebrando o historico unico que RF08/RF13 prometem.
        """

        url = f"{self._base_url}/api/v1/demands/{demand_id}/artifacts"
        async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
            response = await client.get(url)
            if response.status_code == httpx.codes.NOT_FOUND:
                return None
            response.raise_for_status()
            body = response.json()
        artifacts = body if isinstance(body, list) else []
        for artifact in artifacts:
            if isinstance(artifact, dict) and artifact.get("type") == artifact_type:
                artifact_id = artifact.get("id")
                return str(artifact_id) if artifact_id is not None else None
        return None

    async def reprocess_artifact(self, artifact_id: str, payload: dict[str, Any]) -> None:
        """Acrescenta ao artefato existente uma nova versao de origem IA (RF17 consolidado).

        Mesmo ``payload`` de ``persist_artifact``, sem ``type``/``title`` - o
        artefato ja existe, so a versao e nova.
        """

        url = f"{self._base_url}/api/v1/artifacts/{artifact_id}/reprocess"
        async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()

    async def list_demand_segments(self, demand_id: str) -> list[dict[str, Any]]:
        """Lista os trechos citaveis de todas as fontes da demanda (card #160/#161).

        Devolve lista vazia se a demanda nao tiver trecho persistido ainda -
        card #160 so gera embedding do que a captacao ja persistiu
        (``source_segments``); demanda sem trecho simplesmente nao tem o que
        indexar, e quem chama decide o que fazer (#161 cai para o texto
        completo nesse caso).

        Levanta ``httpx.HTTPError`` em falha de rede; devolve lista vazia em
        404 (demanda inexistente aqui e so uma demanda sem trecho, do ponto de
        vista deste cliente - quem valida a existencia da demanda e quem
        chamou, antes de pedir a estruturacao).
        """

        url = f"{self._base_url}/api/v1/demands/{demand_id}/segments"
        async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
            response = await client.get(url)
            if response.status_code == httpx.codes.NOT_FOUND:
                return []
            response.raise_for_status()
            body = response.json()
            return body if isinstance(body, list) else []

    async def save_segment_embeddings(self, embeddings: list[dict[str, Any]]) -> None:
        """Persiste em lote os embeddings gerados para trechos ja captados (card #160).

        ``embeddings`` e a lista de ``{segment_id, model, vector}`` no formato
        de ``SegmentEmbeddingBatchCreate``. Par (trecho, modelo) ja gravado
        responde 409 (append-only: trocar de modelo soma uma linha nova, nunca
        substitui) - tratado aqui como sucesso silencioso, porque reprocessar
        uma demanda cuja embeddagem ja rodou nao e falha, e repetir a chamada
        tem que ser seguro (idempotente do ponto de vista de quem chama).
        """

        if not embeddings:
            return
        url = f"{self._base_url}/api/v1/segment-embeddings"
        async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
            response = await client.post(url, json={"embeddings": embeddings})
            if response.status_code == httpx.codes.CONFLICT:
                return
            response.raise_for_status()

    async def search_similar_segments(
        self,
        demand_id: str,
        *,
        model: str,
        vector: list[float],
        top_k: int,
        min_similarity: float,
    ) -> list[dict[str, Any]]:
        """Busca os trechos da demanda mais proximos do vetor de consulta (card #161).

        Devolve lista vazia quando a demanda nao tem embedding gravado para
        ``model`` - e o sinal que #161 usa para cair no caminho de texto
        completo em vez de montar um contexto vazio.
        """

        url = f"{self._base_url}/api/v1/demands/{demand_id}/segment-embeddings/search"
        payload = {
            "model": model,
            "vector": vector,
            "top_k": top_k,
            "min_similarity": min_similarity,
        }
        async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
            response = await client.post(url, json=payload)
            if response.status_code == httpx.codes.NOT_FOUND:
                return []
            response.raise_for_status()
            body = response.json()
            resultados = body.get("results") if isinstance(body, dict) else None
            return resultados if isinstance(resultados, list) else []
