"""Modelo ORM: usuario da plataforma (RF16, RNF10).

Tabela ``users``. Campos previstos: id, nome, e-mail (unico), hash da senha,
papel, ativo, timestamps.

A senha e sempre armazenada como hash - nunca em texto claro (RNF10, RNF11).
A autenticacao em si (emissao e validacao de token) e responsabilidade do
gateway-service; aqui fica apenas o cadastro que sustenta a autoria dos
registros de auditoria (RF07).

TODO(scaffolding): implementar a classe ``User``.
"""
