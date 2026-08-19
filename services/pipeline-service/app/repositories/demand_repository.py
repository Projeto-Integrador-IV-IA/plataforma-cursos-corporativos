"""Persistencia de demandas (RF02, RF03, RF04).

Operacoes previstas: criar, obter por id, atualizar, listar com filtro por
status, cliente e periodo (RF03), e carregar o detalhe completo com historico e
artefatos atrelados (RF04).

Atencao ao alvo de latencia do CRM (RNF07: 500 ms): a listagem precisa de
indice por (client_id, status, created_at) e nao pode carregar historico.

TODO(scaffolding): implementar.
"""
