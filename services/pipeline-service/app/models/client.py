"""Modelo ORM: empresa cliente (RF01).

Tabela ``clients``. Campos previstos: id (UUID), nome corporativo, CNPJ
(opcional), segmento/nicho, contato principal, observacoes, timestamps de
criacao e atualizacao, autor da criacao.

Relacionamento: 1:N com ``demands``, com integridade referencial garantida no
banco (RNF08). Cliente com demandas nao pode ser removido fisicamente.

TODO(scaffolding): implementar a classe ``Client``.
"""
