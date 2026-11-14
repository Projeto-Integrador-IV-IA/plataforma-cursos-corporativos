"""Configuracao do ingestion-service obtida exclusivamente do ambiente."""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_SOURCE_TEXT_MAX_LENGTH = 50_000


class Settings(BaseSettings):
    """Configuracao do servico e limites operacionais ajustaveis pelo ambiente."""

    model_config = SettingsConfigDict(case_sensitive=False, extra="ignore", frozen=True)

    environment: Literal["development", "test", "staging", "production"]
    log_level: str = Field(min_length=1)
    ingestion_port: int = Field(ge=1, le=65535)
    pipeline_service_url: str = Field(min_length=1)
    pipeline_timeout_seconds: float = Field(default=5.0, gt=0, le=30)
    ai_structuring_service_url: str = Field(min_length=1)
    source_text_max_length: int = Field(default=DEFAULT_SOURCE_TEXT_MAX_LENGTH, ge=10)


@lru_cache
def get_settings() -> Settings:
    """Le e valida o ambiente uma unica vez por processo."""

    return Settings()
