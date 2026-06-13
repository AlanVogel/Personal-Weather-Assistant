"""Tests for health/readiness probes and the request-context middleware."""

from httpx import ASGITransport, AsyncClient

from app.main import create_app


async def test_liveness_ok(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


async def test_readiness_ready_when_clients_initialized(client: AsyncClient) -> None:
    response = await client.get("/health/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["clients_initialized"] is True


async def test_readiness_503_when_clients_missing() -> None:
    # An app whose lifespan never ran has no clients on state.
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/health/ready")
    assert response.status_code == 503
    assert response.json()["clients_initialized"] is False


async def test_response_carries_request_id(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert "X-Request-ID" in response.headers
    assert response.headers["X-Request-ID"]


async def test_supplied_request_id_is_echoed(client: AsyncClient) -> None:
    response = await client.get("/health", headers={"X-Request-ID": "trace-abc-123"})
    assert response.headers["X-Request-ID"] == "trace-abc-123"
