"""Rotas de ingestao (RF09, RF10, RF17).

    POST /api/v1/ingestion/raw-demands            recebe texto bruto e dispara o fluxo
    GET  /api/v1/ingestion/jobs/{id}              estado do processamento (RF17)

O estado retornado alimenta o feedback de execucao exibido na interface
enquanto a estruturacao por IA acontece (RF17, RNF06).

TODO(scaffolding): implementar as rotas conforme o contrato OpenAPI.
"""
