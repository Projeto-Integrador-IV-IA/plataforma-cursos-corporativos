"""DTOs de entrada e saida (Pydantic).

Separados dos modelos ORM de proposito: o que a API expoe e contrato publico
(RNF02) e nao deve mudar so porque o schema do banco mudou.

Convencao de nomes: XxxCreate (entrada de criacao), XxxUpdate (edicao parcial),
XxxRead (saida), XxxDetail (saida com relacionamentos).

TODO(scaffolding): implementar os schemas deste modulo.
"""
