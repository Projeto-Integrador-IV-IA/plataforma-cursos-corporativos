"""Rotas de autenticacao (RF16).

    POST /api/v1/auth/login      autentica e devolve token de acesso
    POST /api/v1/auth/refresh    renova o token
    GET  /api/v1/auth/me         dados do usuario autenticado

Resposta de login invalido nao distingue e-mail inexistente de senha errada
(RNF10).

TODO(scaffolding): implementar as rotas conforme o contrato OpenAPI.
"""
