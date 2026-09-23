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

## Credenciais (RNF11)

`POSTGRES_PASSWORD`, `DATABASE_URL` e `JWT_SECRET_KEY` nao tem valor padrao, nem no `.env.example`
nem no `docker-compose.yml`. Enquanto nao forem preenchidos no `.env`, o Compose interrompe a subida
com `defina <VARIAVEL> no .env` — de proposito, para que nenhum ambiente suba com uma senha conhecida.

```bash
make setup    # cria o .env a partir do template
# preencha POSTGRES_PASSWORD, DATABASE_URL e JWT_SECRET_KEY
make dev
```

## Migrations

Como o banco nao publica porta no host, `make migrate` e `make migration` executam o Alembic num
container efemero do `pipeline-service` (`docker compose run --rm`), que ja esta na rede do banco e
recebe o `DATABASE_URL` do `.env`. A migration gerada aparece em
`services/pipeline-service/app/db/migrations/versions/` pelo volume montado.
