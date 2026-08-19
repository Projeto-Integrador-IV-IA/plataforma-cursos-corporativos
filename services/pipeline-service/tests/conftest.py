"""Fixtures compartilhadas dos testes do pipeline-service.

Fixtures previstas:
    - client: cliente HTTP de teste sobre a aplicacao FastAPI;
    - settings: configuracao apontando para ambiente de teste;
    - dublês dos servicos a jusante, para que o teste de um microsservico nao
      dependa da subida dos outros.

TODO(scaffolding): implementar quando app/main.py existir.
"""
