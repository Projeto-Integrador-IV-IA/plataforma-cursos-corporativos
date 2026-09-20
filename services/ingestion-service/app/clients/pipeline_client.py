"""Cliente HTTP que confirma a persistencia do bruto no pipeline-service."""

from datetime import datetime
from uuid import UUID

import httpx

from app.core.exceptions import UpstreamError
from app.domain.raw_demand import PersistedRawDemand, RawDemand, SourceKind


class PipelineClient:
    """Encapsula o contrato interno sem compartilhar acesso ao banco."""

    def __init__(self, http_client: httpx.Client) -> None:
        self.http_client = http_client

    def persist_raw_demand(
        self,
        raw_demand: RawDemand,
        *,
        author_id: UUID,
        request_id: str | None = None,
    ) -> PersistedRawDemand:
        headers = {"X-User-ID": str(author_id)}
        if request_id:
            headers["X-Request-ID"] = request_id

        try:
            response = self.http_client.post(
                f"/api/v1/demands/{raw_demand.demand_id}/raw-inputs",
                json={
                    "original_content": raw_demand.text,
                    "source": raw_demand.source_type.value,
                },
                headers=headers,
            )
        except httpx.TimeoutException as exc:
            raise UpstreamError(
                status_code=504,
                code="PIPELINE_TIMEOUT",
                message="O pipeline-service nao confirmou a persistencia no prazo.",
            ) from exc
        except httpx.RequestError as exc:
            raise UpstreamError(
                status_code=502,
                code="PIPELINE_UNAVAILABLE",
                message="Nao foi possivel persistir o texto bruto no pipeline-service.",
            ) from exc

        if response.status_code != 201:
            self._raise_response_error(response)

        body = response.json()
        return PersistedRawDemand(
            raw_input_id=UUID(body["id"]),
            demand_id=UUID(body["demand_id"]),
            source_type=SourceKind(body["source"]),
            created_at=datetime.fromisoformat(body["created_at"]),
        )

    @staticmethod
    def _raise_response_error(response: httpx.Response) -> None:
        try:
            error = response.json()["error"]
            code = str(error["code"])
            message = str(error["message"])
            details = error.get("details")
        except (KeyError, TypeError, ValueError):
            code = "PIPELINE_INVALID_RESPONSE"
            message = "O pipeline-service devolveu uma resposta inesperada."
            details = None

        propagated_status = response.status_code if response.status_code in {404, 409, 422} else 502
        raise UpstreamError(
            status_code=propagated_status,
            code=code,
            message=message,
            details=details,
        )
