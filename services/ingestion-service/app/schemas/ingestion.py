"""DTOs da ingestao (Pydantic).

Entrada prevista: demand_id, origem declarada, conteudo bruto.
Saida prevista: identificador do processamento, estado, referencia do artefato
gerado quando concluido.

Estados de processamento (RF17): RECEBIDA, NORMALIZADA, ESTRUTURANDO,
CONCLUIDA, FALHA_ESTRUTURACAO. O estado FALHA_ESTRUTURACAO nao implica perda -
o bruto permanece registrado (RNF05).

TODO(scaffolding): implementar os schemas.
"""
