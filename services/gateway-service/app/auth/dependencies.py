"""Dependencias de autenticacao das rotas (RF16, RNF10).

Fornece a dependencia que extrai e valida o token do header Authorization e
disponibiliza o usuario autenticado para a rota.

Regra: toda rota da plataforma exige autenticacao, exceto login e health.
O padrao e negar - rota nova nasce protegida.

TODO(scaffolding): implementar as dependencias.
"""
