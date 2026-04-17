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

# ── Data Pipeline ──

data-download: ## Download raw medicine dataset from GitHub
	mkdir -p data/raw
	curl -L -o data/raw/indian_medicines.csv "https://raw.githubusercontent.com/junioralive/Indian-Medicine-Dataset/main/DATA/indian_medicine_data.csv"

data-process: ## Process raw CSV into normalized salt compositions + drugs
	python3 data/processors/ingest_medicines.py

data-scrape-stores: ## Scrape Jan Aushadhi stores from genericdrugscan.com (~2hrs)
	python3 data/scrapers/jan_aushadhi.py

data-scrape-nppa: ## Scrape NPPA ceiling prices from laafon.com
	python3 data/scrapers/nppa.py

data-seed: ## Seed PostgreSQL from processed CSVs (needs: make infra + make migrate)
	cd backend && . .venv/bin/activate && python3 ../data/processors/seed_database.py

data-index: ## Index drugs into Meilisearch (needs: make infra)
	cd backend && . .venv/bin/activate && python3 ../data/processors/index_drugs.py

data-geocode: ## Geocode stores with Google Maps API (needs GOOGLE_MAPS_API_KEY)
	python3 data/processors/geocode.py

data-all: data-download data-process ## Download + process (no external services needed)

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
