.PHONY: help setup infra up down dev test lint migrate seed

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

# ── Setup ──

setup: ## Initial project setup (venv + deps)
	cd backend && python -m venv .venv && . .venv/bin/activate && pip install -e ".[dev,data]"
	@echo "✓ Backend venv created. Activate with: source backend/.venv/bin/activate"
	@[ -f .env ] || cp .env.example .env && echo "✓ Created .env from .env.example — fill in your API keys"

# ── Infrastructure ──

infra: ## Start PostgreSQL, Redis, Meilisearch via Docker
	docker compose up -d

down: ## Stop all Docker services
	docker compose down

up: infra ## Alias for infra

# ── Development ──

dev: ## Run the FastAPI dev server with hot reload
	cd backend && . .venv/bin/activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# ── Database ──

migrate: ## Run database migrations
	cd backend && . .venv/bin/activate && alembic upgrade head

migration: ## Create a new migration (usage: make migration msg="add users table")
	cd backend && . .venv/bin/activate && alembic revision --autogenerate -m "$(msg)"

# ── Testing ──

test: ## Run all tests
	cd backend && . .venv/bin/activate && pytest -v

test-cov: ## Run tests with coverage
	cd backend && . .venv/bin/activate && pytest --cov=app --cov-report=term-missing

# ── Linting ──

lint: ## Run ruff linter + formatter check
	cd backend && . .venv/bin/activate && ruff check . && ruff format --check .

fmt: ## Auto-format code with ruff
	cd backend && . .venv/bin/activate && ruff check --fix . && ruff format .
