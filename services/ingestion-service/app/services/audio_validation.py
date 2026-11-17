"""Valida o arquivo real; nome e Content-Type sozinhos nao provam formato."""

import math
import wave
from hashlib import sha256
from io import BytesIO
from pathlib import PurePosixPath
from uuid import UUID

import mutagen
from mutagen.flac import FLAC
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4
from mutagen.oggopus import OggOpus
from mutagen.oggvorbis import OggVorbis
from mutagen.wave import WAVE

from app.core.config import Settings
from app.core.exceptions import PlatformError
from app.domain.audio import AudioSource

FORMATS = {
    ".wav": ((WAVE,), "audio/wav", {"audio/wav", "audio/x-wav", "audio/wave"}),
    ".mp3": ((MP3,), "audio/mpeg", {"audio/mpeg", "audio/mp3"}),
    ".m4a": ((MP4,), "audio/mp4", {"audio/mp4", "audio/x-m4a"}),
    ".ogg": ((OggVorbis, OggOpus), "audio/ogg", {"audio/ogg", "application/ogg"}),
    ".flac": ((FLAC,), "audio/flac", {"audio/flac", "audio/x-flac"}),
}


def reject_audio(code: str, message: str, status_code: int = 422) -> PlatformError:
    return PlatformError(status_code=status_code, code=code, message=message)


def validate_audio(
    *,
    demand_id: UUID,
    filename: str | None,
    content_type: str | None,
    content: bytes,
    settings: Settings,
) -> AudioSource:
    """Mede duracao no arquivo, sem aceitar duracao declarada pelo operador."""

    if len(content) > settings.audio_max_bytes:
        raise reject_audio(
            "AUDIO_TOO_LARGE",
            f"O audio deve conter no maximo {settings.audio_max_bytes} bytes.",
            413,
        )
    name = PurePosixPath((filename or "").replace("\\", "/")).name
    suffix = PurePosixPath(name).suffix.lower()
    if suffix not in FORMATS or len(name) > 255 or any(ord(char) < 32 for char in name):
        raise reject_audio("AUDIO_INVALID_FORMAT", "Use um arquivo WAV, MP3, M4A, OGG ou FLAC.")
    classes, canonical_type, mime_types = FORMATS[suffix]
    mime_type = (content_type or "application/octet-stream").split(";", 1)[0].lower().strip()
    if mime_type not in mime_types | {"application/octet-stream"}:
        raise reject_audio("AUDIO_INVALID_FORMAT", "O tipo informado nao corresponde ao audio.")
    try:
        audio = mutagen.File(BytesIO(content), options=[WAVE, MP3, MP4, OggVorbis, OggOpus, FLAC])
        if not isinstance(audio, classes):
            raise ValueError("formato diferente da extensao")
        if isinstance(audio, WAVE):
            with wave.open(BytesIO(content), "rb") as pcm:
                expected = pcm.getnframes() * pcm.getnchannels() * pcm.getsampwidth()
                if len(pcm.readframes(pcm.getnframes())) != expected:
                    raise ValueError("WAV incompleto")
        duration = float(audio.info.length)
        if not math.isfinite(duration) or duration <= 0:
            raise ValueError("duracao invalida")
    except (mutagen.MutagenError, OSError, ValueError, EOFError, wave.Error) as exc:
        raise reject_audio(
            "AUDIO_INVALID_FORMAT", "O arquivo esta vazio, corrompido ou nao e um audio valido."
        ) from exc
    if duration > settings.audio_max_duration_seconds:
        raise reject_audio(
            "AUDIO_TOO_LONG",
            f"O audio deve durar no maximo {settings.audio_max_duration_seconds:g} segundos.",
        )
    return AudioSource(
        demand_id, name, canonical_type, content, duration, sha256(content).hexdigest()
    )
