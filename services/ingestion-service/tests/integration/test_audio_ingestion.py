"""Aceite RF30 na fronteira HTTP: valida o arquivo e exige confirmacao duravel."""

from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.api.v1.routes.ingestion import get_pipeline_client
from app.clients.pipeline_client import PipelineClient
from app.core.config import get_settings
from app.core.exceptions import UpstreamError
from app.domain.audio import AudioSource
from app.main import create_app
from app.schemas.ingestion import AudioPersistenceRead

FIXTURES = Path(__file__).resolve().parents[4] / "tests/fixtures/audio"


class AudioPipeline:
    def __init__(self) -> None:
        self.calls: list[AudioSource] = []
        self.error: UpstreamError | None = None

    def persist_audio(self, audio: AudioSource, *, author_id, request_id=None):
        self.calls.append(audio)
        if self.error:
            raise self.error
        return AudioPersistenceRead(
            id=uuid4(),
            demand_id=audio.demand_id,
            source="AUDIO",
            author_id=author_id,
            received_order=1,
            created_at=datetime.now(UTC),
            audio={
                "filename": audio.filename,
                "content_type": audio.content_type,
                "size_bytes": len(audio.content),
                "duration_seconds": audio.duration_seconds,
                "sha256": audio.sha256,
            },
        )


@pytest.fixture(autouse=True)
def environment(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    for key, value in {
        "ENVIRONMENT": "test",
        "LOG_LEVEL": "INFO",
        "INGESTION_PORT": "8002",
        "PIPELINE_SERVICE_URL": "http://pipeline",
        "AI_STRUCTURING_SERVICE_URL": "http://ai",
        "AUDIO_MAX_BYTES": "25000000",
        "AUDIO_MAX_DURATION_SECONDS": "3600",
    }.items():
        monkeypatch.setenv(key, value)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def pipeline() -> AudioPipeline:
    return AudioPipeline()


@pytest.fixture
def api(pipeline: AudioPipeline) -> Iterator[TestClient]:
    app = create_app()
    app.dependency_overrides[get_pipeline_client] = lambda: pipeline
    with TestClient(app) as client:
        yield client


def upload(api: TestClient, content: bytes, filename="tone.wav", mime="audio/wav"):
    return api.post(
        "/api/v1/ingestion/audio",
        files={"file": (filename, content, mime)},
        data={"demand_id": str(uuid4())},
        headers={"X-User-ID": str(uuid4()), "X-Request-ID": "rf30-upload"},
    )


@pytest.mark.parametrize(
    "extension,mime",
    [
        ("wav", "audio/wav"),
        ("mp3", "audio/mpeg"),
        ("m4a", "audio/mp4"),
        ("ogg", "audio/ogg"),
        ("flac", "audio/flac"),
    ],
)
def test_valid_audio_is_preserved_with_audio_provenance(api, pipeline, extension, mime):
    content = (FIXTURES / f"tone.{extension}").read_bytes()
    response = upload(api, content, f"tone.{extension}", mime)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["source_type"] == "AUDIO"
    assert body["transcription_status"] == "PENDENTE"
    assert body["audio"]["size_bytes"] == len(content)
    assert body["audio"]["duration_seconds"] > 0
    assert pipeline.calls[0].content == content


@pytest.mark.parametrize(
    "filename,mime,content",
    [
        ("tone.txt", "text/plain", b"not audio"),
        ("tone.wav", "audio/wav", b""),
        ("tone.wav", "audio/wav", b"RIFF" + b"x" * 100),
        ("tone.wav", "text/plain", (FIXTURES / "tone.wav").read_bytes()),
        ("tone.mp3", "audio/mpeg", (FIXTURES / "tone.wav").read_bytes()),
        ("tone.wav", "audio/wav", (FIXTURES / "tone.wav").read_bytes()[:100]),
    ],
    ids=["extension", "empty", "corrupt-header", "mime", "disguised", "truncated"],
)
def test_invalid_format_never_reaches_persistence(api, pipeline, filename, mime, content):
    response = upload(api, content, filename, mime)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "AUDIO_INVALID_FORMAT"
    assert response.json()["error"]["message"]
    assert response.json()["error"]["request_id"] == "rf30-upload"
    assert pipeline.calls == []


def test_exact_size_and_duration_are_accepted_then_excess_is_refused(api, pipeline, monkeypatch):
    content = (FIXTURES / "tone.wav").read_bytes()
    monkeypatch.setenv("AUDIO_MAX_BYTES", str(len(content)))
    monkeypatch.setenv("AUDIO_MAX_DURATION_SECONDS", "1")
    assert upload(api, content).status_code == 201
    get_settings.cache_clear()
    monkeypatch.setenv("AUDIO_MAX_BYTES", str(len(content) - 1))
    response = upload(api, content)
    assert response.status_code == 413
    assert str(len(content) - 1) in response.json()["error"]["message"]
    get_settings.cache_clear()
    monkeypatch.setenv("AUDIO_MAX_BYTES", str(len(content)))
    monkeypatch.setenv("AUDIO_MAX_DURATION_SECONDS", "0.5")
    response = upload(api, content)
    assert response.status_code == 422
    assert "0.5 segundos" in response.json()["error"]["message"]
    assert len(pipeline.calls) == 1


@pytest.mark.parametrize("status,code", [(504, "PIPELINE_TIMEOUT"), (502, "PIPELINE_UNAVAILABLE")])
def test_failed_persistence_never_confirms_receipt(api, pipeline, status, code):
    pipeline.error = UpstreamError(status_code=status, code=code, message="Nao confirmado.")
    response = upload(api, (FIXTURES / "tone.wav").read_bytes())
    assert response.status_code == status
    assert response.json()["error"]["code"] == code


def test_missing_metadata_is_refused(api, pipeline):
    response = api.post("/api/v1/ingestion/audio", files={"file": ("tone.wav", b"data")})
    assert response.status_code == 422
    assert pipeline.calls == []


def test_audio_cannot_be_declared_in_the_text_endpoint(api):
    response = api.post(
        "/api/v1/ingestion",
        json={"text": "texto suficiente", "source_type": "AUDIO", "demand_id": str(uuid4())},
        headers={"X-User-ID": str(uuid4())},
    )
    assert response.status_code == 422
    schema = api.get("/openapi.json").json()["components"]["schemas"]["IngestionCreate"]
    source_options = schema["properties"]["source_type"]["anyOf"][0]["enum"]
    assert "AUDIO" not in source_options


@pytest.mark.parametrize("reply", [httpx.Response(201, json={}), httpx.Response(500)])
def test_client_refuses_invalid_confirmation(reply):
    with httpx.Client(
        transport=httpx.MockTransport(lambda _: reply), base_url="http://pipeline"
    ) as http:
        audio = AudioSource(uuid4(), "tone.wav", "audio/wav", b"bytes", 1, "a" * 64)
        with pytest.raises(UpstreamError) as error:
            PipelineClient(http).persist_audio(audio, author_id=uuid4())
    assert error.value.status_code == 502


@pytest.mark.parametrize(
    "name,value",
    [
        ("AUDIO_MAX_BYTES", "0"),
        ("AUDIO_MAX_BYTES", "-1"),
        ("AUDIO_MAX_BYTES", "1.5"),
        ("AUDIO_MAX_BYTES", "abc"),
        ("AUDIO_MAX_DURATION_SECONDS", "0"),
        ("AUDIO_MAX_DURATION_SECONDS", "-1"),
        ("AUDIO_MAX_DURATION_SECONDS", "nan"),
        ("AUDIO_MAX_DURATION_SECONDS", "inf"),
    ],
)
def test_invalid_limits_are_configuration_errors(monkeypatch, name, value):
    monkeypatch.setenv(name, value)
    with pytest.raises(ValidationError):
        get_settings()


def test_audio_limits_have_documented_defaults(monkeypatch):
    monkeypatch.delenv("AUDIO_MAX_BYTES")
    monkeypatch.delenv("AUDIO_MAX_DURATION_SECONDS")
    assert get_settings().audio_max_bytes == 25_000_000
    assert get_settings().audio_max_duration_seconds == 3600
