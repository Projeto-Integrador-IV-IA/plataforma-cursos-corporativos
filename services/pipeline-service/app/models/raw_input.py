"""Modelo ORM: demanda bruta recebida (RF09).

Tabela ``raw_inputs``. Guarda o texto heterogeneo exatamente como chegou
(e-mail colado, transcricao de reuniao, mensagens) antes de qualquer
normalizacao ou envio ao LLM.

Campos previstos: id, demand_id (FK), conteudo original, origem declarada,
conteudo normalizado, timestamp e autor.

Este registro e a garantia de RNF05: se a chamada ao LLM falhar ou estourar o
timeout, a demanda bruta ja esta persistida e nada se perde.

TODO(scaffolding): implementar a classe ``RawInput``.
"""
