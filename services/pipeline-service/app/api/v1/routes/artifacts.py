"""Rotas de artefatos e versoes (RF08, RF13, RF15).

    POST /api/v1/demands/{id}/artifacts          anexa artefato a demanda
    GET  /api/v1/demands/{id}/artifacts          lista artefatos da demanda
    GET  /api/v1/artifacts/{id}/versions         lista versoes
    GET  /api/v1/artifacts/{id}/versions/{n}     recupera versao especifica
    POST /api/v1/artifacts/{id}/versions         cria nova versao apos revisao (RF14)

TODO(scaffolding): implementar as rotas conforme o contrato OpenAPI.
"""
