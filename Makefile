# =============================================================================
# Atalhos de desenvolvimento. Uso: make help
# =============================================================================
SHELL := /bin/bash
SERVICES := gateway-service ingestion-service ai-structuring-service pipeline-service

.DEFAULT_GOAL := help
.PHONY: help setup install install-py install-web dev up down logs db-up db-shell \
        migrate migration test test-py test-web lint fmt check clean

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

dev: ## Sobe todos os servicos + frontend via Docker Compose
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

migrate: ## Aplica as migrations no banco
	cd services/pipeline-service && alembic upgrade head

migration: ## Gera nova migration. Uso: make migration m="descricao"
	cd services/pipeline-service && alembic revision --autogenerate -m "$(m)"

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

check: lint test ## Portao de qualidade local (rode antes de abrir PR)

clean: ## Remove artefatos de build e caches
	find . -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .ruff_cache web/dist
