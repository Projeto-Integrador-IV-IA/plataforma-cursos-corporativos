"""Mapa de roteamento do gateway.

Declara qual prefixo de caminho pertence a qual microsservico interno. Fica em
um unico lugar para que a topologia seja legivel e para que adicionar um
servico novo (evolucao futura, RNF13) nao exija caçar rotas pelo codigo.

Mapa previsto:
    /api/v1/clients      -> pipeline-service
    /api/v1/demands      -> pipeline-service
    /api/v1/artifacts    -> pipeline-service
    /api/v1/ingestion    -> ingestion-service
    /api/v1/structuring  -> ai-structuring-service

As URLs de destino vem de variavel de ambiente (RNF11).

TODO(scaffolding): implementar o mapa.
"""
