"""Configuracao de log estruturado.

Todos os microsservicos emitem log em formato consistente para que o fluxo de
uma demanda possa ser reconstruido de ponta a ponta entre servicos - insumo
direto da trilha de auditoria (RNF09) e do diagnostico de falhas do LLM (RNF05).

Contrato esperado desta camada:
    - saida em JSON com: timestamp, nivel, servico, mensagem, ``request_id``,
      ``demand_id`` (quando houver) e duracao em milissegundos;
    - ``request_id`` propagado entre servicos pelo header ``X-Request-ID``;
    - nivel controlado por ``LOG_LEVEL``;
    - nenhum dado sensivel de cliente ou chave de API no log (RNF10, RNF11).

TODO(scaffolding): implementar ``configure_logging()`` e ``get_logger()``.
"""

# TODO: def configure_logging(level: str) -> None: ...
# TODO: def get_logger(name: str): ...
