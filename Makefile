.DEFAULT_GOAL := ajuda
SHELL := /bin/bash

VENV    ?= .venv
PY      := $(VENV)/bin/python
PIP     := $(VENV)/bin/pip
BACKEND := backend

export DATABASE_URL ?= postgresql+psycopg://assessoria:assessoria@127.0.0.1:5432/assessoria
export TEST_DATABASE_URL ?= postgresql+psycopg://assessoria:assessoria@127.0.0.1:5432/assessoria_test

.PHONY: ajuda instalar dev api test test-unit test-agentes lint migrate revision seed limpar

ajuda:  ## lista os alvos
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
	  | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

$(VENV):
	python3 -m venv $(VENV)
	$(PIP) install --quiet --upgrade pip

instalar: $(VENV)  ## instala as dependências do backend
	$(PIP) install --quiet -e "$(BACKEND)[dev]"

dev: instalar  ## sobe a API em modo recarga
	cd $(BACKEND) && ../$(VENV)/bin/uvicorn app.main:app --reload --port 8000

api: dev  ## apelido de `dev`

test:  ## suíte completa
	cd $(BACKEND) && DATABASE_URL=$(TEST_DATABASE_URL) ../$(PY) -m pytest -q

test-unit:  ## só os motores — sem banco, sem rede
	cd $(BACKEND) && ../$(PY) -m pytest -q tests/unit

test-agentes:  ## suíte de aceite de linguagem natural (Fase 5)
	@echo "A suíte de agentes entra na Fase 5 (docs/ESPEC.md §9)."

lint:  ## ruff + mypy
	cd $(BACKEND) && ../$(VENV)/bin/ruff check app tests && ../$(VENV)/bin/mypy app

migrate:  ## aplica as migrations
	cd $(BACKEND) && ../$(VENV)/bin/alembic upgrade head

revision:  ## nova migration: make revision m="descricao"
	cd $(BACKEND) && ../$(VENV)/bin/alembic revision --autogenerate -m "$(m)"

seed:  ## conta demo com dados sintéticos (Fase 3)
	@echo "O seed entra junto com o painel, na Fase 3."

limpar:
	find . -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache $(BACKEND)/.pytest_cache $(BACKEND)/.ruff_cache $(BACKEND)/.mypy_cache
