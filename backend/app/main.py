from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from app.api.routes import chat, drugs, health, waitlist, webhook
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

app.include_router(health.router, tags=["health"])
app.include_router(webhook.router, tags=["whatsapp"])
app.include_router(drugs.router)
app.include_router(chat.router)
app.include_router(waitlist.router)
