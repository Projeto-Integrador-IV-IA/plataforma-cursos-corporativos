# Ambiente de desenvolvimento

Atende **RNF01** (reprodução local da composição dos microsserviços) e **RNF11** (credenciais só
no `.env`). A composição descrita aqui é a do #141 (card #64).

## Pré-requisitos

| Ferramenta | Versão | Para quê |
|---|---|---|
| Git | 2.40+ | Controle de versão |
| Docker Desktop | 26+ (Engine) | Banco e orquestração local |
| Docker Compose | v2.24+ | Orquestração de múltiplos contêineres |
| Python | 3.12+ | Microsserviços |
| Node.js | 20+ | Frontend |
| GitHub CLI (`gh`) | opcional | Criar PR pelo terminal |

## Primeira configuração

```bash
git clone <url-do-repositorio>
cd plataforma-cursos-corporativos
cp .env.example .env
```

Abra o `.env` e preencha os valores locais. **Nunca versione este arquivo** (RNF11) — ele já está no
`.gitignore`, e a CI reprova o PR se ele aparecer.

Três campos são obrigatórios e não têm valor padrão: `POSTGRES_PASSWORD`, `DATABASE_URL` e
`JWT_SECRET_KEY`. Enquanto estiverem vazios, o Docker Compose interrompe qualquer comando com
`defina <VARIAVEL> no .env`.

- `DATABASE_URL` segue o formato indicado no próprio template, com a mesma senha de
  `POSTGRES_PASSWORD` e o host `db`.
- `JWT_SECRET_KEY` precisa de pelo menos 32 caracteres. Para gerar:
  `python -c "import secrets; print(secrets.token_urlsafe(48))"`.

Os campos sensíveis do template ficam vazios de propósito. Gere valores fortes localmente e
distribua-os por um gerenciador de segredos. O Docker Compose injeta o `.env` nos processos; a
aplicação não carrega arquivos nem possui fallback para chaves, tokens ou credenciais.

Chave da API de linguagem: solicite à gerência. Enquanto não tiver, use `LLM_PROVIDER=mock`, que
funciona sem chave e sem custo.

```bash
make install     # dependências dos 4 serviços + frontend (lint e testes no host)
make migrate     # aplica as migrations — o Alembic roda num container e sobe o banco se preciso
make dev         # sobe o banco e os quatro microsserviços
```

Os quatro serviços sobem e respondem `GET /health`; as rotas de negócio ainda estão sendo
implementadas. Depois da subida, `docker compose ps` deve mostrar os cinco containers como
`healthy`. O frontend roda fora do Compose:

```bash
cd web && npm run dev
```

## Portas

Só o `gateway-service` publica porta no host. Os demais serviços e o banco ficam na rede privada do
Compose e se enxergam pelo nome (`pipeline-service`, `db` etc.) — ver
[topologia local](../../infra/docker/README.md).

| Serviço | Porta | Acesso a partir do host |
|---|---|---|
| `web` | 5173 | http://localhost:5173 (fora do Compose) |
| `gateway-service` | 8000 | http://localhost:8000/docs |
| `pipeline-service` | 8001 | só pela rede do Compose |
| `ingestion-service` | 8002 | só pela rede do Compose |
| `ai-structuring-service` | 8003 | só pela rede do Compose |
| PostgreSQL | 5432 | só pela rede do Compose |

`/docs` traz a documentação interativa da API, gerada automaticamente (RNF02). Para consultar um
serviço interno, use `docker compose exec <servico> ...`.

## Comandos do dia a dia

```bash
make help        # lista tudo
make check       # lint + testes — rode antes de abrir PR
make logs        # acompanha os logs da stack
make db-shell    # abre o psql
make migration m="descricao"   # cria nova migration
make down        # derruba a stack
```

## Trabalhar em um serviço isolado

Exporte no shell todas as variáveis listadas no `.env.example` do serviço antes de iniciar. Os
templates são somente documentação e nunca são carregados automaticamente pela aplicação.

```bash
cd services/pipeline-service
pip install -e ".[dev]"
uvicorn app.main:app --reload --port "$PIPELINE_PORT"
```

Use ambiente virtual por serviço (`python -m venv .venv`) para não misturar dependências.

Um serviço rodando no host não alcança o PostgreSQL do Compose, que não publica porta. Para o
`pipeline-service` com banco, prefira `make dev` e acompanhe com `make logs`.

## Editor

O repositório traz [extensões recomendadas](../../.vscode/extensions.json) e um
[exemplo de configuração](../../.vscode/settings.example.json) para VS Code. Copie:

```bash
cp .vscode/settings.example.json .vscode/settings.json
```

`.editorconfig` garante UTF-8, quebra de linha LF e indentação consistentes em qualquer editor.

## Windows

O projeto é desenvolvido em Windows e roda em Linux nos containers. Dois cuidados:

- **Quebra de linha.** O `.editorconfig` força LF. Se o Git converter para CRLF, o container quebra:

  ```bash
  git config --global core.autocrlf input
  ```

- **Docker Desktop** precisa do WSL2 habilitado.

## Problemas comuns

| Sintoma | Causa provável | Solução |
|---|---|---|
| `port is already allocated` | Porta ocupada por outra execução | `make down`, ou ajuste a porta no `.env` |
| Serviço não conecta no banco | `DATABASE_URL` apontando para `localhost` dentro do container | Dentro do Compose o host é `db`, não `localhost` |
| `.env` não carregado | Arquivo não existe | `make setup` |
| `defina POSTGRES_PASSWORD no .env` (ou `DATABASE_URL`, `JWT_SECRET_KEY`) | Campo obrigatório vazio | Preencha no `.env` |
| `password authentication failed` | O volume `pgdata` foi criado com outra senha — o Postgres só aplica `POSTGRES_PASSWORD` na primeira inicialização | `make down` e `docker volume rm cursos-corporativos_pgdata` (**apaga os dados locais**) |
| `http://localhost:8001/docs` não abre | Só o gateway publica porta no host | Use o gateway ou `docker compose exec` |
| Migration não aplica | `DATABASE_URL` com senha diferente de `POSTGRES_PASSWORD` | Confira os dois no `.env` |
| Chamada ao LLM falha | Chave ausente ou inválida | Use `LLM_PROVIDER=mock` para desenvolver |
