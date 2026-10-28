"""Configuracao do ai-structuring-service obtida exclusivamente do ambiente."""

from functools import lru_cache
from typing import Final, Literal, Self

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

#: Provedores cujo ``LLM_BASE_URL`` pode ficar vazio (a classe do provedor traz o padrao).
PROVEDORES_COM_ENDPOINT_PADRAO: Final[frozenset[str]] = frozenset({"openrouter"})


class Settings(BaseSettings):
    """Variaveis obrigatorias do servico; a chave da LLM fica mascarada."""

    model_config = SettingsConfigDict(case_sensitive=False, extra="ignore", frozen=True)

    environment: Literal["development", "test", "staging", "production"]
    log_level: str = Field(min_length=1)
    ai_structuring_port: int = Field(ge=1, le=65535)
    pipeline_service_url: str = Field(min_length=1)
    llm_provider: str = Field(default="mock", min_length=1)
    llm_model: str = Field(min_length=1)
    llm_api_key: SecretStr | None
    llm_base_url: str | None = None
    llm_completions_path: str = Field(default="/chat/completions", min_length=1)
    llm_http_referer: str | None = None
    llm_app_title: str | None = None
    llm_timeout_seconds: float = Field(gt=0)
    llm_max_retries: int = Field(ge=0)
    llm_schema_max_retries: int = Field(ge=0)
    llm_temperature: float = Field(ge=0, le=2)

    @field_validator("llm_api_key", mode="before")
    @classmethod
    def empty_api_key_is_absent(cls, value: object) -> object:
        """Permite chave vazia somente para o provedor local mock."""

        return None if value == "" else value

    @field_validator("llm_base_url", "llm_http_referer", "llm_app_title", mode="before")
    @classmethod
    def empty_base_url_is_absent(cls, value: object) -> object:
        """Trata endpoint e cabecalhos de atribuicao vazios como ausentes."""

        return None if value == "" else value

    @model_validator(mode="after")
    def require_api_key_for_remote_provider(self) -> Self:
        """Falha rapidamente se um provedor remoto estiver sem credencial."""

        if self.llm_provider.casefold() != "mock" and self.llm_api_key is None:
            raise ValueError("LLM_API_KEY e obrigatoria para provedores remotos")
        return self

    @model_validator(mode="after")
    def require_base_url_for_remote_provider(self) -> Self:
        """Falha rapidamente se um provedor remoto estiver sem endpoint.

        O endpoint vem do ambiente para que trocar de fornecedor seja
        configuracao, nao alteracao de codigo (RNF03). Provedores com endpoint
        publico conhecido (``openrouter``) dispensam a variavel.
        """

        nome = self.llm_provider.casefold()
        dispensa_endpoint = nome == "mock" or nome in PROVEDORES_COM_ENDPOINT_PADRAO
        if not dispensa_endpoint and self.llm_base_url is None:
            raise ValueError("LLM_BASE_URL e obrigatoria para provedores remotos")
        return self

    @property
    def is_mock_provider(self) -> bool:
        """Indica se o provedor selecionado dispensa rede e credencial."""

        return self.llm_provider.casefold() == "mock"


@lru_cache
def get_settings() -> Settings:
    """Le e valida o ambiente uma unica vez por processo."""

    return Settings()
