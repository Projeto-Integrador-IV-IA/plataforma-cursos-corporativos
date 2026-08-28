"""Configuracao do pipeline-service.

Toda a configuracao chega por variavel de ambiente (RNF11: nenhum segredo no
codigo-fonte). O template das variaveis fica em .env.example, na raiz do
repositorio; nenhum valor real deve ser versionado.

Contrato esperado desta camada:
    - classe Settings baseada em pydantic_settings.BaseSettings;
    - leitura do arquivo .env em desenvolvimento e do ambiente em producao;
    - validacao na inicializacao - o servico falha rapido se faltar variavel
      obrigatoria, em vez de quebrar no meio de uma requisicao;
    - instancia unica cacheada, importada pelos demais modulos.

Variaveis consumidas por este servico:
    ENVIRONMENT, LOG_LEVEL, SERVICE_PORT (8001 por padrao) e as especificas
    documentadas no README do servico.

TODO(scaffolding): implementar Settings e get_settings().
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    environment: str = "development"
    log_level: str = "INFO"
    service_port: int = 8001
    database_url: str

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
