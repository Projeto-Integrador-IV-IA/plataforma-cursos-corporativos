"""Cliente HTTP que confirma a persistencia do bruto no pipeline-service."""

from datetime import datetime
from uuid import UUID

import httpx
from pydantic import ValidationError

from app.core.exceptions import UpstreamError
from app.domain.audio import AudioSource
from app.domain.raw_demand import PersistedRawDemand, RawDemand, SourceKind
from app.schemas.ingestion import AudioPersistenceRead


class PipelineClient:
    """Encapsula o contrato interno sem compartilhar acesso ao banco."""

    def __init__(self, http_client: httpx.Client) -> None:
        self.http_client = http_client

    def persist_audio(
        self, audio: AudioSource, *, author_id: UUID, request_id: str | None = None
    ) -> AudioPersistenceRead:
        """A resposta 201 so vale depois de confirmar o arquivo e a proveniencia."""

        headers = {"X-User-ID": str(author_id)}
        if request_id:
            headers["X-Request-ID"] = request_id
        try:
            response = self.http_client.post(
                f"/api/v1/demands/{audio.demand_id}/audio-inputs",
                files={"file": (audio.filename, audio.content, audio.content_type)},
                data={"duration_seconds": str(audio.duration_seconds)},
                headers=headers,
            )
        except httpx.TimeoutException as exc:
            raise UpstreamError(
                status_code=504,
                code="PIPELINE_TIMEOUT",
                message="O pipeline nao confirmou a persistencia do audio no prazo.",
            ) from exc
        except httpx.RequestError as exc:
            raise UpstreamError(
                status_code=502,
                code="PIPELINE_UNAVAILABLE",
                message="Nao foi possivel persistir o audio no pipeline.",
            ) from exc
        if response.status_code != 201:
            self._raise_response_error(response)
        try:
            receipt = AudioPersistenceRead.model_validate_json(response.content)
            if (
                receipt.demand_id != audio.demand_id
                or receipt.author_id != author_id
                or receipt.audio.sha256 != audio.sha256
                or receipt.audio.size_bytes != len(audio.content)
                or receipt.audio.filename != audio.filename
                or receipt.audio.content_type != audio.content_type
                or receipt.audio.duration_seconds != audio.duration_seconds
            ):
                raise ValueError("Confirmacao de outro arquivo ou proveniencia")
        except (ValidationError, ValueError) as exc:
            raise UpstreamError(
                status_code=502,
                code="PIPELINE_INVALID_RESPONSE",
                message="O pipeline nao confirmou a integridade do audio.",
            ) from exc
        return receipt

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
                    **(
                        {"previous_attempt_id": str(raw_demand.previous_attempt_id)}
                        if raw_demand.previous_attempt_id is not None
                        else {}
                    ),
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
            previous_attempt_id=(
                UUID(body["previous_attempt_id"]) if body.get("previous_attempt_id") else None
            ),
        )

    def persist_normalization(
        self,
        raw_input_id: UUID,
        normalized_content: str,
        *,
        request_id: str | None = None,
    ) -> None:
        """Grava a copia sanitizada sem reenviar ou substituir o texto original."""

        headers = {"X-Request-ID": request_id} if request_id else None
        try:
            response = self.http_client.patch(
                f"/api/v1/raw-inputs/{raw_input_id}/normalization",
                json={"normalized_content": normalized_content},
                headers=headers,
            )
        except httpx.TimeoutException as exc:
            raise UpstreamError(
                status_code=504,
                code="PIPELINE_TIMEOUT",
                message="O pipeline-service nao confirmou a normalizacao no prazo.",
            ) from exc
        except httpx.RequestError as exc:
            raise UpstreamError(
                status_code=502,
                code="PIPELINE_UNAVAILABLE",
                message="Nao foi possivel persistir o texto normalizado no pipeline-service.",
            ) from exc

        if response.status_code != 200:
            self._raise_response_error(response)

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
