# =============================================================================
# Atalhos de desenvolvimento. Uso: make help
# =============================================================================
SHELL := /bin/bash
SERVICES := gateway-service ingestion-service ai-structuring-service pipeline-service

.DEFAULT_GOAL := help
.PHONY: help setup install install-py install-web dev up down logs db-up db-shell \
        migrate migration test test-py test-web lint fmt security check clean

help: ## Lista os comandos disponiveis
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	 awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

setup: ## Cria o .env a partir do template (nao sobrescreve)
	@test -f .env || cp .env.example .env

install: install-py install-web ## Instala dependencias de todos os servicos e do frontend

install-py: ## Instala dependencias Python de cada microsservico
	@for s in $(SERVICES); do echo ">> $$s"; (cd services/$$s && pip install -e ".[dev]"); done

install-web: ## Instala dependencias do frontend
	cd web && npm install

dev: ## Sobe o banco e os quatro microsservicos via Docker Compose
	docker compose up --build

up: ## Sobe a stack em background
	docker compose up -d --build

down: ## Derruba a stack
	docker compose down

logs: ## Acompanha os logs da stack
	docker compose logs -f

db-up: ## Sobe apenas o PostgreSQL
	docker compose up -d db

db-shell: ## Abre o psql no banco local
	docker compose exec db psql -U $${POSTGRES_USER} -d $${POSTGRES_DB}

# O banco nao publica porta no host (so o gateway publica), entao o Alembic roda
# num container efemero do pipeline-service, dentro da rede do Compose. O codigo
# e montado por volume: a migration gerada aparece direto em versions/.
migrate: ## Aplica as migrations no banco
	docker compose run --rm pipeline-service alembic upgrade head

migration: ## Gera nova migration. Uso: make migration m="descricao"
	docker compose run --rm pipeline-service alembic revision --autogenerate -m "$(m)"

test: test-py test-web ## Roda toda a suite de testes

test-py: ## Testes dos microsservicos
	@for s in $(SERVICES); do echo ">> $$s"; (cd services/$$s && pytest -q); done

test-web: ## Testes do frontend
	cd web && npm run test

lint: ## Verifica estilo e tipos
	ruff check services
	cd web && npm run lint

fmt: ## Formata o codigo
	ruff format services
	cd web && npm run format

security: ## Reprova arquivos sensiveis ou credenciais aparentes versionadas
	@proibidos=$$(git ls-files | grep -E '(^|/)\.env($$|\.)|\.(pem|key|p12|pfx)$$' | grep -vE '(^|/)\.env\.example$$' || true); \
	 test -z "$$proibidos" || { echo "Arquivos sensiveis versionados:"; echo "$$proibidos"; exit 1; }
	@# No DSN, usuario e senha precisam ser literais: `$${VAR}` e `<placeholder>`
	@# sao template, nao credencial.
	@padrao='(sk-[A-Za-z0-9_-]{16,}|AKIA[0-9A-Z]{16}|AIza[0-9A-Za-z_-]{35}|gh[pousr]_[A-Za-z0-9_]{20,}|xox[baprs]-[A-Za-z0-9-]{10,}|eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}|-----BEGIN [A-Z ]*PRIVATE KEY-----|[a-z][a-z0-9+.-]*://[^[:space:]/$$<{]+:[^@[:space:]$$<{]+@)'; \
	 if git grep -nEI "$$padrao" -- ':!*.example' ':!.github/workflows/*' ':!Makefile' ':!web/package-lock.json'; then \
	   echo "Credencial aparente na arvore de trabalho:"; exit 1; \
	 fi
	@# Historico: so o que esta branch acrescenta sobre a dev.
	@padrao2='(sk-[A-Za-z0-9_-]{16,}|AKIA[0-9A-Z]{16}|AIza[0-9A-Za-z_-]{35}|gh[pousr]_[A-Za-z0-9_]{20,}|xox[baprs]-[A-Za-z0-9-]{10,}|eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}|-----BEGIN [A-Z ]*PRIVATE KEY-----|[a-z][a-z0-9+.-]*://[^[:space:]/$$<{]+:[^@[:space:]$$<{]+@)'; \
	 base=$$(git merge-base origin/dev HEAD 2>/dev/null); \
	 if [ -z "$$base" ]; then \
	   echo "sem origin/dev para comparar; varredura limitada a arvore"; exit 0; \
	 fi; \
	 adicionado=$$(git diff --unified=0 "$$base...HEAD" -- . ':(exclude)*.example' ':(exclude).github/workflows/**' ':(exclude)Makefile' ':(exclude)web/package-lock.json' | grep -E '^[+][^+]' || true); \
	 if printf "%s\n" "$$adicionado" | grep -qE "$$padrao2"; then \
	   echo "Credencial aparente nos commits desta branch:"; \
	   printf "%s\n" "$$adicionado" | grep -E "$$padrao2"; exit 1; \
	 fi

check: security lint test ## Portao de qualidade local (rode antes de abrir PR)

clean: ## Remove artefatos de build e caches
	find . -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .ruff_cache web/dist
