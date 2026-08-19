"""DTOs da estruturacao (Pydantic).

Entrada: demand_id, texto normalizado, versao de prompt a usar.
Saida: curso estruturado (ver ``app.domain.course``), metadados de execucao
(modelo, versao de prompt, tokens, latencia) e lista de campos ausentes.

Os metadados de execucao acompanham o artefato gravado para que qualquer
resultado possa ser reproduzido e auditado depois (RNF04, RNF09).

TODO(scaffolding): implementar os schemas.
"""
