"""Per-IP rate limiting for the expensive LLM endpoints."""

from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette import status

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def _client_identifier(request: Request) -> str:
    """Identify the caller for rate limiting.

    Railway (and most PaaS proxies) put the real client IP first in the
    ``X-Forwarded-For`` header; ``request.client.host`` would otherwise be the
    proxy's address, so every caller would share one bucket.
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return get_remote_address(request)


_settings = get_settings()

# In-memory limiter: per-process, which is correct for a single Railway instance.
# For multiple instances, point slowapi at Redis via ``storage_uri``.
limiter = Limiter(
    key_func=_client_identifier,
    enabled=_settings.rate_limit_enabled,
)


async def rate_limit_exceeded_handler(request: Request, exc: Exception) -> JSONResponse:
    """Return the project's standard JSON error shape for 429s."""
    detail = "Too many requests. Please slow down and try again shortly."
    if isinstance(exc, RateLimitExceeded):
        logger.info("rate_limited", path=request.url.path, detail=str(exc))
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={"error": "RateLimitExceeded", "detail": detail},
    )
