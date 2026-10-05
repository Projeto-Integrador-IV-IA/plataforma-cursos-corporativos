"""Configuracao do pipeline-service obtida exclusivamente do ambiente."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Variaveis obrigatorias do pipeline; credenciais sao mascaradas em logs."""

    model_config = SettingsConfigDict(case_sensitive=False, extra="ignore", frozen=True)

    environment: Literal["development", "test", "staging", "production"]
    log_level: str = Field(min_length=1)
    pipeline_port: int = Field(ge=1, le=65535)
    database_url: SecretStr = Field(min_length=1)


@lru_cache
def get_settings() -> Settings:
    """Le e valida o ambiente uma unica vez por processo."""

    return Settings()
