"""Adaptador HTTP para o formato comum do ``ai-structuring-service`` (RF11)."""

from collections.abc import Iterable
from typing import Any
from uuid import UUID

import httpx
from pydantic import BaseModel, ConfigDict, Field

from app.core.exceptions import UpstreamError
from app.normalizers.text_normalizer import concatenate_normalized_sources


class StructuringRequest(BaseModel):
    """Entrada interna comum validada antes de atravessar a rede.

    O modelo espelha os campos obrigatorios e os limites publicados em
    ``packages/contracts/openapi/ai-structuring-service.yaml``. A versao do
    prompt e opcional no contrato e, quando omitida aqui, fica sob o default do
    servico de IA.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, frozen=True)

    demand_id: str = Field(min_length=1, max_length=64)
    text: str = Field(min_length=1, max_length=50_000)
    source_ids: tuple[str, ...] = Field(default_factory=tuple, max_length=100)


class AIClient:
    """Envia apenas requisicoes que obedecem ao contrato da estruturacao."""

    def __init__(self, http_client: httpx.Client) -> None:
        self.http_client = http_client

    @staticmethod
    def build_request(
        demand_id: UUID | str,
        normalized_sources: Iterable[str],
        *,
        source_ids: Iterable[UUID | str] = (),
    ) -> StructuringRequest:
        """Concatena fontes em ordem e valida o corpo canonico da requisicao."""

        return StructuringRequest(
            demand_id=str(demand_id),
            text=concatenate_normalized_sources(normalized_sources),
            source_ids=tuple(str(source_id) for source_id in source_ids),
        )

    def structure_course(
        self,
        demand_id: UUID | str,
        normalized_sources: Iterable[str],
        *,
        source_ids: Iterable[UUID | str] = (),
        request_id: str | None = None,
    ) -> dict[str, Any]:
        """Executa a estruturacao sincrona e devolve a resposta JSON do servico."""

        payload = self.build_request(demand_id, normalized_sources, source_ids=source_ids)
        headers = {"X-Request-ID": request_id} if request_id else None

        try:
            response = self.http_client.post(
                "/api/v1/structuring",
                json=payload.model_dump(mode="json"),
                headers=headers,
            )
        except httpx.TimeoutException as exc:
            raise UpstreamError(
                status_code=504,
                code="AI_STRUCTURING_TIMEOUT",
                message="O ai-structuring-service nao respondeu no prazo.",
            ) from exc
        except httpx.RequestError as exc:
            raise UpstreamError(
                status_code=502,
                code="AI_STRUCTURING_UNAVAILABLE",
                message="Nao foi possivel chamar o ai-structuring-service.",
            ) from exc

        if response.status_code != 200:
            self._raise_response_error(response)

        try:
            body = response.json()
        except ValueError as exc:
            raise UpstreamError(
                status_code=502,
                code="AI_STRUCTURING_INVALID_RESPONSE",
                message="O ai-structuring-service devolveu uma resposta inesperada.",
            ) from exc
        if not isinstance(body, dict):
            raise UpstreamError(
                status_code=502,
                code="AI_STRUCTURING_INVALID_RESPONSE",
                message="O ai-structuring-service devolveu uma resposta inesperada.",
            )
        return body

    @staticmethod
    def _raise_response_error(response: httpx.Response) -> None:
        try:
            error = response.json()["error"]
            code = str(error["code"])
            message = str(error["message"])
            details = error.get("details")
        except (KeyError, TypeError, ValueError):
            code = "AI_STRUCTURING_INVALID_RESPONSE"
            message = "O ai-structuring-service devolveu uma resposta inesperada."
            details = None

        propagated_status = (
            response.status_code if response.status_code in {422, 429, 502, 503, 504} else 502
        )
        raise UpstreamError(
            status_code=propagated_status,
            code=code,
            message=message,
            details=details,
        )
