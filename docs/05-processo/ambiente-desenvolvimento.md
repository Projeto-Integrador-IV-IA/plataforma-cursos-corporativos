# Ambiente de desenvolvimento

## Pré-requisitos

| Ferramenta | Versão | Para quê |
|---|---|---|
| Git | 2.40+ | Controle de versão |
| Docker Desktop | recente | Banco e orquestração local |
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

Os campos sensíveis do template ficam vazios de propósito. Gere valores fortes localmente e
distribua-os por um gerenciador de segredos. O Docker Compose injeta o `.env` nos processos; a
aplicação não carrega arquivos nem possui fallback para chaves, tokens ou credenciais.

Chave da API de linguagem: solicite à gerência. Enquanto não tiver, use `LLM_PROVIDER=mock`, que
funciona sem chave e sem custo.

```bash
make install     # dependências dos 4 serviços + frontend
make db-up       # sobe apenas o PostgreSQL
make migrate     # aplica as migrations
make dev         # sobe a stack completa
```

> **Hoje** apenas `make db-up` funciona: os serviços ainda são scaffolding, sem implementação.

## Portas

| Serviço | Porta | URL |
|---|---|---|
| `web` | 5173 | http://localhost:5173 |
| `gateway-service` | 8000 | http://localhost:8000/docs |
| `pipeline-service` | 8001 | http://localhost:8001/docs |
| `ingestion-service` | 8002 | http://localhost:8002/docs |
| `ai-structuring-service` | 8003 | http://localhost:8003/docs |
| PostgreSQL | 5432 | |

`/docs` traz a documentação interativa da API, gerada automaticamente (RNF02).

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
| Migration não aplica | Banco não subiu | `make db-up` e aguarde o healthcheck |
| Chamada ao LLM falha | Chave ausente ou inválida | Use `LLM_PROVIDER=mock` para desenvolver |
