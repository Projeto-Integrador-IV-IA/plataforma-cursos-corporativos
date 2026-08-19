"""Rotas de demandas (RF02, RF03, RF04, RF09).

    POST   /api/v1/demands                    cria negociacao vinculada a cliente
    GET    /api/v1/demands                    lista por status, cliente e periodo
    GET    /api/v1/demands/{id}               detalhe com historico e artefatos
    PATCH  /api/v1/demands/{id}               edita dados da negociacao
    POST   /api/v1/demands/{id}/raw-inputs    registra demanda bruta (RF09, RNF05)

TODO(scaffolding): implementar as rotas conforme o contrato OpenAPI.
"""
