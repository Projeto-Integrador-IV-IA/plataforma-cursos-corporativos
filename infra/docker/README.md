# Recursos de container

Cada microsservico tem seu proprio `Dockerfile`, junto do codigo. A orquestracao local fica no
[`docker-compose.yml`](../../docker-compose.yml) da raiz e atende ao RNF01.

## Topologia local

Os quatro backends e o PostgreSQL compartilham a rede bridge `services-network`. Os nomes dos
servicos no Compose sao os nomes DNS internos; todas as URLs sao injetadas por variaveis de
ambiente. Apenas o `gateway-service` publica uma porta no host.

O `pipeline-service` e o unico container de aplicacao que recebe `DATABASE_URL`. Os demais
containers recebem somente as URLs REST das dependencias que consomem, conforme o ADR-0004.

## Execucao e saude

```bash
make dev
```

Cada backend declara um healthcheck que consulta o proprio `GET /health`. Depois da subida,
`docker compose ps` deve mostrar `healthy` para os quatro servicos e para o banco. O endpoint
publico do gateway tambem pode ser conferido em `http://localhost:8000/health` (ou na porta
definida por `GATEWAY_PORT`).

Para conferir um endpoint interno diretamente:

```bash
docker compose exec pipeline-service python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8001/health').read().decode())"
```

Os valores `change-me-local-only` do `.env.example` existem apenas para a primeira subida local.
Ambientes compartilhados devem fornecer credenciais proprias e nao versionadas.
