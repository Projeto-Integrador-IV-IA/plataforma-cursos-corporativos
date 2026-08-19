"""Provedor de LLM sobre API HTTP.

Implementacao concreta da interface definida em ``base.py``. O fornecedor
especifico e a familia de modelo sao decididos na avaliacao comparativa da
Fase 2 e chegam por configuracao (``LLM_PROVIDER``, ``LLM_MODEL``) - nunca
fixados no codigo, para que trocar de fornecedor nao exija reescrever o
servico (RNF13).

Chave lida de ``LLM_API_KEY`` (RNF11) - nunca embutida no codigo.

Pontos de atencao:
    - timeout configuravel por ``LLM_TIMEOUT_SECONDS``, alinhado ao alvo de
      15 s de RNF06;
    - retentativa com backoff limitada por ``LLM_MAX_RETRIES``, sem retentar
      erro de entrada invalida;
    - temperatura baixa e saida validada contra o JSON Schema, para garantir
      formato previsivel (RNF03);
    - contabilizacao de tokens por chamada, insumo do levantamento de custo
      de operacao (RNF12).

TODO(scaffolding): implementar o provedor apos a escolha do fornecedor.
"""
