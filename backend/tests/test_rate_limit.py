"""Tests for rate-limit client identification and the 429 response shape.

These cover our own glue — the proxy-aware key function and the JSON error
response. Enforcement of the limit itself is slowapi's responsibility and is
exercised live in production, not re-tested here.
"""

import httpx
from httpx import AsyncClient
from starlette.requests import Request

from app.core import rate_limit
from app.core.config import get_settings
from app.core.rate_limit import _client_identifier, rate_limit_exceeded_handler


def _request_with(headers: dict[str, str], client_host: str = "10.0.0.1") -> Request:
    raw_headers = [(k.lower().encode(), v.encode()) for k, v in headers.items()]
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/recommendations",
        "headers": raw_headers,
        "client": (client_host, 12345),
    }
    return Request(scope)


def test_client_identifier_prefers_first_forwarded_for() -> None:
    # Behind Railway's proxy, the real client IP is first in X-Forwarded-For.
    request = _request_with({"x-forwarded-for": "203.0.113.7, 10.0.0.1"})
    assert _client_identifier(request) == "203.0.113.7"


def test_client_identifier_falls_back_to_peer_address() -> None:
    request = _request_with({}, client_host="198.51.100.9")
    assert _client_identifier(request) == "198.51.100.9"


async def test_handler_returns_standard_json_error_shape() -> None:
    request = _request_with({})

    response = await rate_limit_exceeded_handler(request, ValueError("boom"))

    assert response.status_code == 429
    body = httpx.Response(429, content=response.body).json()
    assert body["error"] == "RateLimitExceeded"
    assert "Too many requests" in body["detail"]


async def test_exceeding_limit_returns_429(client: AsyncClient) -> None:
    """End-to-end: once a client crosses the limit, it gets a 429 (not a 200)."""
    limit_count = int(get_settings().rate_limit.split("/")[0])
    headers = {"X-Forwarded-For": "203.0.113.200"}  # unique IP → own bucket

    rate_limit.limiter.enabled = True
    try:
        statuses = [
            (
                await client.post("/api/recommendations", json={"city": "Zagreb"}, headers=headers)
            ).status_code
            for _ in range(limit_count + 1)
        ]
    finally:
        rate_limit.limiter.enabled = False

    assert statuses[0] == 200
    assert statuses[-1] == 429
    assert statuses.count(200) == limit_count
