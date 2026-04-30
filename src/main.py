import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from openai import AsyncOpenAI

from src.api.middleware import configure_middleware
from src.api.routes.chat import router as chat_router
from src.api.routes.health import router as health_router
from src.core.config import get_settings
from src.core.logging_config import setup_logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    setup_logging(app_env=settings.app_env, log_level=settings.log_level)
    app.state.openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
    logger.info(
        "Application started",
        extra={"env": settings.app_env, "model": settings.openai_model},
    )
    yield
    await app.state.openai_client.close()
    logger.info("Application stopped")


app = FastAPI(
    title="Andela MCP Assessment API",
    version="1.0.0",
    lifespan=lifespan,
)

configure_middleware(app)
app.include_router(health_router)
app.include_router(chat_router)
