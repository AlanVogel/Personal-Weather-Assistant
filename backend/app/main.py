"""FastAPI application entry point with proper lifecycle management."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded

from app.core.config import get_settings
from app.core.dependencies import get_lifespan_clients, shutdown_lifespan_clients
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.core.middleware import RequestContextMiddleware
from app.core.rate_limit import limiter, rate_limit_exceeded_handler
from app.health.router import router as health_router
from app.recommendations.router import router as recommendations_router
from app.weather.router import router as weather_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifecycle. Initialize clients on startup, cleanup on shutdown."""
    configure_logging()
    logger = get_logger(__name__)

    logger.info("application_starting")
    settings = get_settings()

    # Initialize long-lived async clients in app state
    app.state.clients = await get_lifespan_clients(settings)

    logger.info("application_ready", env=settings.environment)

    yield

    logger.info("application_shutting_down")
    await shutdown_lifespan_clients(app.state.clients)
    logger.info("application_stopped")


def create_app() -> FastAPI:
    """Application factory pattern. Allows different configurations for tests vs prod."""
    settings = get_settings()

    app = FastAPI(
        title="Personal Weather Assistant",
        description="Weather data combined with AI-powered personalized recommendations",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        # No cookies or auth headers are used, so credentials aren't needed.
        # Keeping this False also avoids the wildcard-origin restriction.
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    app.add_middleware(RequestContextMiddleware)

    # Per-IP rate limiting (applied via decorators on the LLM endpoints).
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

    register_exception_handlers(app)

    app.include_router(health_router)
    app.include_router(weather_router)
    app.include_router(recommendations_router)

    return app


app = create_app()
