"""Rotas de movimentacao no pipeline (RF05, RF06, RF07).

    POST /api/v1/demands/{id}/transitions   move de etapa (avanco ou retrocesso)
    GET  /api/v1/demands/{id}/transitions   historico completo, ordem cronologica

O corpo da transicao carrega etapa de destino e motivo; o autor vem do token
autenticado, nunca do corpo da requisicao (RNF10).

TODO(scaffolding): implementar as rotas conforme o contrato OpenAPI.
"""
