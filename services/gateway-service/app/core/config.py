"""Configuracao do gateway-service obtida exclusivamente do ambiente."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Variaveis obrigatorias do gateway; segredos sao mascarados em logs."""

    model_config = SettingsConfigDict(case_sensitive=False, extra="ignore", frozen=True)

    environment: Literal["development", "test", "staging", "production"]
    log_level: str = Field(min_length=1)
    gateway_port: int = Field(ge=1, le=65535)
    pipeline_service_url: str = Field(min_length=1)
    ingestion_service_url: str = Field(min_length=1)
    ai_structuring_service_url: str = Field(min_length=1)
    jwt_secret_key: SecretStr = Field(min_length=32)
    jwt_algorithm: Literal["HS256", "HS384", "HS512"]
    access_token_expire_minutes: int = Field(gt=0)


@lru_cache
def get_settings() -> Settings:
    """Le e valida o ambiente uma unica vez por processo."""

    return Settings()
