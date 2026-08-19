"""Rota generica de encaminhamento aos servicos internos.

Captura os caminhos declarados em ``app.proxy.routes_map`` e delega ao
forwarder, sempre depois da verificacao de autenticacao.

Nenhuma regra de negocio mora aqui: o gateway roteia e autentica, nao decide
sobre dominio (RNF01, RNF13).

TODO(scaffolding): implementar a rota.
"""
