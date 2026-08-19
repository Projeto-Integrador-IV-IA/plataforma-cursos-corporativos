"""Caso de uso: autenticacao do operador (RF16, RNF10).

Fluxo de login: buscar usuario ativo pelo e-mail, verificar a senha contra o
hash, emitir o token. Falha em qualquer passo produz a mesma resposta generica.

O cadastro de usuarios mora no pipeline-service; este servico o consulta por
API (RNF01).

TODO(scaffolding): implementar o caso de uso.
"""
