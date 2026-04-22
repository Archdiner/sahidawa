from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import chat, health, waitlist
from app.core.config import settings

structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger = structlog.get_logger()
    logger.info("sahidawa_starting", env=settings.app_env)
    yield
    # Shutdown
    logger.info("sahidawa_shutting_down")


app = FastAPI(
    title="SahiDawa API",
    description="Medicine price discovery and generic substitution platform",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, tags=["health"])
app.include_router(chat.router)
app.include_router(waitlist.router)

try:
    from app.api.routes import webhook
    app.include_router(webhook.router, tags=["whatsapp"])
except Exception:
    pass  # WhatsApp webhook needs DB — disabled without infrastructure

try:
    from app.api.routes import drugs
    app.include_router(drugs.router)
except Exception:
    pass  # Meilisearch not available — drugs search endpoint disabled
