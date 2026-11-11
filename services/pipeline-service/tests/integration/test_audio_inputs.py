"""RF30: arquivo e proveniencia sobrevivem em transacao independente do STT."""

from collections.abc import Iterator
from hashlib import sha256
from pathlib import Path
from uuid import UUID, uuid4

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import AudioInput, Demand, RawInput, User

FIXTURES = Path(__file__).resolve().parents[4] / "tests/fixtures/audio"
CONTENT = (FIXTURES / "tone.wav").read_bytes()


@pytest.fixture
def engine(tmp_path, monkeypatch) -> Iterator[Engine]:
    """Banco descartavel; downgrade com audio e recusado para nao perder fontes."""

    url = f"sqlite+pysqlite:///{(tmp_path / 'audio.sqlite3').as_posix()}"
    for key, value in {
        "ENVIRONMENT": "test",
        "LOG_LEVEL": "INFO",
        "PIPELINE_PORT": "8001",
        "DATABASE_URL": url,
        "AUTH_SERVICE_KEY": "chave-interna-de-teste-com-32-caracteres",
        "AUDIO_MAX_BYTES": "25000000",
        "AUDIO_MAX_DURATION_SECONDS": "3600",
    }.items():
        monkeypatch.setenv(key, value)
    get_settings.cache_clear()
    command.upgrade(Config("alembic.ini"), "head")
    database = sa.create_engine(url, connect_args={"check_same_thread": False})

    @sa.event.listens_for(database, "connect")
    def foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    yield database
    database.dispose()
    get_settings.cache_clear()


@pytest.fixture
def ids(engine, company):
    with Session(engine) as session:
        user = User(name="Operador", email="audio@example.com", password_hash="hash")
        demand = Demand(client_id=company, title="Reuniao gravada")
        session.add_all([user, demand])
        session.commit()
        return demand.id, user.id


def upload(api, ids, content=CONTENT, duration="1"):
    demand, user = ids
    return api.post(
        f"/api/v1/demands/{demand}/audio-inputs",
        files={"file": ("reuniao.wav", content, "audio/wav")},
        data={"duration_seconds": duration},
        headers={"X-User-ID": str(user)},
    )


def test_committed_bytes_and_provenance_are_available_before_transcription(api, engine, ids):
    response = upload(api, ids)
    assert response.status_code == 201, response.text
    body = response.json()
    source_id = UUID(body["id"])
    assert body["source"] == "AUDIO"
    assert body["author_id"] == str(ids[1])
    assert body["demand_id"] == str(ids[0])
    assert body["received_order"] == 1
    assert body["created_at"]
    assert body["original_content"] == ""
    assert body["normalized_content"] is None
    assert body["audio"]["sha256"] == sha256(CONTENT).hexdigest()
    # Um consumidor futuro ve os bytes ja commitados em outra transacao.
    with Session(engine) as consumer:
        stored = consumer.get(AudioInput, source_id)
        assert stored.content == CONTENT
        consumer.rollback()
    downloaded = api.get(f"/api/v1/raw-inputs/{source_id}/audio")
    assert downloaded.status_code == 200
    assert downloaded.content == CONTENT
    assert downloaded.headers["x-content-sha256"] == sha256(CONTENT).hexdigest()
    assert api.get(f"/api/v1/raw-inputs/{source_id}").json()["audio"] == body["audio"]
    detail = api.get(f"/api/v1/demands/{ids[0]}").json()["raw_inputs"][0]
    assert detail["source"] == "AUDIO"
    assert detail["audio"]["filename"] == "reuniao.wav"
    assert "content" not in detail["audio"]


def test_audio_and_text_share_the_same_receipt_order(api, ids):
    demand, user = ids
    text = api.post(
        f"/api/v1/demands/{demand}/raw-inputs",
        json={"original_content": "Texto da fonte", "source": "EMAIL"},
        headers={"X-User-ID": str(user)},
    )
    assert text.status_code == 201
    assert upload(api, ids).json()["received_order"] == 2


@pytest.mark.parametrize("which", [0, 1])
def test_missing_parent_does_not_leave_audio_or_source(api, engine, ids, which):
    invalid = list(ids)
    invalid[which] = uuid4()
    assert upload(api, invalid).status_code == 404
    with Session(engine) as session:
        assert session.scalar(sa.select(sa.func.count()).select_from(AudioInput)) == 0
        assert session.scalar(sa.select(sa.func.count()).select_from(RawInput)) == 0


@pytest.mark.parametrize(
    "content,duration",
    [(b"", "1"), (CONTENT, "0"), (CONTENT, "3601")],
    ids=["empty", "zero-duration", "too-long"],
)
def test_invalid_audio_metadata_is_refused(api, ids, content, duration):
    assert upload(api, ids, content=content, duration=duration).status_code == 422


def test_database_refuses_overwriting_or_deleting_original_bytes(api, engine, ids):
    source_id = UUID(upload(api, ids).json()["id"])
    for statement in (
        "UPDATE audio_inputs SET content = :content WHERE raw_input_id = :id",
        "DELETE FROM audio_inputs WHERE raw_input_id = :id",
    ):
        with engine.connect() as connection:
            with pytest.raises(sa.exc.IntegrityError, match="imutavel"):
                connection.execute(sa.text(statement), {"content": b"changed", "id": source_id.hex})
            connection.rollback()
    assert api.get(f"/api/v1/raw-inputs/{source_id}/audio").content == CONTENT


def test_source_insert_rolls_back_when_audio_insert_fails(api, engine, ids, monkeypatch):
    from app.services import raw_input_service

    def fail(**_kwargs):
        raise RuntimeError("falha ao gravar binario")

    monkeypatch.setattr(raw_input_service, "AudioInput", fail)
    with pytest.raises(RuntimeError, match="falha ao gravar binario"):
        upload(api, ids)
    with Session(engine) as session:
        assert session.scalar(sa.select(sa.func.count()).select_from(RawInput)) == 0


def test_downgrade_is_refused_when_it_would_lose_audio(api, engine, ids):
    assert upload(api, ids).status_code == 201
    with pytest.raises(RuntimeError, match="Downgrade recusado"):
        command.downgrade(Config("alembic.ini"), "20261101_1300")
    assert api.get(f"/api/v1/demands/{ids[0]}").json()["raw_inputs"][0]["source"] == "AUDIO"
