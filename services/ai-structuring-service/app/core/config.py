"""Configuracao do ai-structuring-service.

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
    ENVIRONMENT, LOG_LEVEL, SERVICE_PORT (8003 por padrao) e as especificas
    documentadas no README do servico.

TODO(scaffolding): implementar Settings e get_settings().
"""

# TODO: from pydantic_settings import BaseSettings, SettingsConfigDict
# TODO: class Settings(BaseSettings): ...
# TODO: def get_settings() -> Settings: ...
