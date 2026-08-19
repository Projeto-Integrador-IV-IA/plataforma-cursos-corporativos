"""Modelo ORM: historico de transicoes de etapa (RF07).

Tabela ``stage_transitions``, append-only: nunca sofre UPDATE nem DELETE.
E a trilha de auditoria exigida por RNF09.

Campos previstos: id, demand_id (FK), etapa de origem, etapa de destino, autor,
instante e motivo (obrigatorio no retrocesso - RF06).

TODO(scaffolding): implementar a classe ``StageTransition``.
"""
