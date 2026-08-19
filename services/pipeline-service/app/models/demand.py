"""Modelo ORM: demanda / negociacao (RF02).

Tabela ``demands``. Campos previstos: id (UUID), client_id (FK obrigatoria),
titulo, etapa atual do pipeline, status, responsavel, timestamps.

A etapa atual e um campo desnormalizado por desempenho (RNF07): a verdade
historica esta em ``stage_transitions`` (RF07, RNF09), e os dois nunca podem
divergir - a atualizacao acontece na mesma transacao.

TODO(scaffolding): implementar a classe ``Demand``.
"""
