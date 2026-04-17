# SahiDawa

Medicine price discovery and generic substitution platform for India.

## Project Structure

- `backend/` — FastAPI backend (Python 3.11+)
- `data/` — Data pipeline: scrapers, processors, seed data
- `web/` — Landing page (to be built)
- `docker-compose.yml` — PostgreSQL+PostGIS, Redis, Meilisearch

## Dev Setup

```bash
make setup    # create venv, install deps, copy .env
make infra    # start postgres, redis, meilisearch
make migrate  # run database migrations
make dev      # start fastapi with hot reload
```

## Stack

- **Backend:** FastAPI + SQLAlchemy (async) + Alembic
- **Database:** PostgreSQL with PostGIS extension
- **Search:** Meilisearch (typo-tolerant drug search)
- **Cache:** Redis
- **LLM:** Groq API (Llama 3.1 8B) for input parsing and response generation
- **WhatsApp:** Meta Cloud API via webhooks

## Conventions

- All DB models in `backend/app/models/`
- API routes in `backend/app/api/routes/`
- Business logic in `backend/app/services/` (organized by domain)
- Use `ruff` for linting and formatting
- Async everywhere — async DB sessions, async HTTP clients
- Environment config via `.env` loaded by pydantic-settings
