"""Health check endpoints for monitoring and deployment platforms."""

from fastapi import APIRouter, Request, Response, status
from pydantic import BaseModel

from app import __version__

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    version: str
    service: str


class ReadinessResponse(BaseModel):
    status: str
    clients_initialized: bool


@router.get("/", response_model=HealthResponse)
async def root() -> HealthResponse:
    """Root endpoint. Useful for basic uptime monitoring."""
    return HealthResponse(status="ok", version=__version__, service="weather-assistant")


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Liveness probe. Returns 200 if the process is running."""
    return HealthResponse(status="healthy", version=__version__, service="weather-assistant")


@router.get("/health/ready", response_model=ReadinessResponse)
async def readiness(request: Request, response: Response) -> ReadinessResponse:
    """Readiness probe.

    Reports whether the long-lived clients (httpx, Groq) have been initialized
    by the lifespan handler. Unlike liveness, a 503 here tells an orchestrator
    not to route traffic yet. It deliberately does not call the external APIs,
    so probes don't consume free-tier quota.
    """
    clients = getattr(request.app.state, "clients", None)
    ready = clients is not None and clients.http_client is not None
    if not ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return ReadinessResponse(
        status="ready" if ready else "not_ready",
        clients_initialized=ready,
    )
