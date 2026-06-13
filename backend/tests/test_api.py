"""End-to-end API tests using HTTPX AsyncClient with ASGI transport."""

from datetime import date, timedelta

from httpx import AsyncClient


class TestHealthEndpoints:
    async def test_root_returns_ok(self, client: AsyncClient) -> None:
        response = await client.get("/")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert "version" in body

    async def test_health_returns_healthy(self, client: AsyncClient) -> None:
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


class TestWeatherEndpoint:
    async def test_get_weather_returns_snapshot(self, client: AsyncClient) -> None:
        response = await client.get("/api/weather", params={"city": "Zagreb"})
        assert response.status_code == 200
        body = response.json()
        assert body["city"] == "Zagreb"
        assert "current" in body
        assert "forecast" in body

    async def test_missing_city_returns_422(self, client: AsyncClient) -> None:
        response = await client.get("/api/weather")
        assert response.status_code == 422


class TestRecommendationsEndpoint:
    async def test_post_recommendation_returns_combined(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/recommendations",
            json={"city": "Zagreb"},
        )
        assert response.status_code == 200
        body = response.json()
        assert "weather" in body
        assert "recommendation" in body
        assert "target_date" in body
        assert body["recommendation"]["summary"]

    async def test_post_with_target_date(self, client: AsyncClient) -> None:
        target = (date.today() + timedelta(days=2)).isoformat()
        response = await client.post(
            "/api/recommendations",
            json={"city": "Zagreb", "target_date": target},
        )
        assert response.status_code == 200
        assert response.json()["target_date"] == target

    async def test_rejects_past_date(self, client: AsyncClient) -> None:
        past = (date.today() - timedelta(days=1)).isoformat()
        response = await client.post(
            "/api/recommendations",
            json={"city": "Zagreb", "target_date": past},
        )
        assert response.status_code == 400
        assert "past" in response.json()["detail"].lower()

    async def test_rejects_date_beyond_forecast(self, client: AsyncClient) -> None:
        far = (date.today() + timedelta(days=20)).isoformat()
        response = await client.post(
            "/api/recommendations",
            json={"city": "Zagreb", "target_date": far},
        )
        assert response.status_code == 400

    async def test_empty_city_rejected(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/recommendations",
            json={"city": ""},
        )
        assert response.status_code == 422

    async def test_extra_fields_rejected(self, client: AsyncClient) -> None:
        """Strict DTOs prevent typos and silent acceptance of unknown fields."""
        response = await client.post(
            "/api/recommendations",
            json={"city": "Zagreb", "unknown_field": "value"},
        )
        assert response.status_code == 422

    async def test_followup_returns_answer(
        self,
        client: AsyncClient,
        sample_recommendation: dict,  # type: ignore[type-arg]
    ) -> None:
        # First, get a recommendation
        rec_response = await client.post("/api/recommendations", json={"city": "Zagreb"})
        prev = rec_response.json()["recommendation"]

        # Then, ask follow-up
        response = await client.post(
            "/api/recommendations/followup",
            json={
                "city": "Zagreb",
                "target_date": date.today().isoformat(),
                "previous_recommendation": prev,
                "user_question": "What about cycling tomorrow?",
            },
        )
        assert response.status_code == 200
        assert "answer" in response.json()

    async def test_followup_short_question_rejected(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/recommendations/followup",
            json={
                "city": "Zagreb",
                "target_date": date.today().isoformat(),
                "previous_recommendation": {
                    "summary": "A summary that is long enough.",
                    "clothing": {
                        "items": ["jacket"],
                        "reasoning": "Because it is cold outside today.",
                    },
                    "activities": {
                        "suggested": ["walk"],
                        "reasoning": "Mild conditions are good for walking around.",
                    },
                    "health_tips": [],
                    "weekly_advice": None,
                },
                "user_question": "x",  # too short
            },
        )
        assert response.status_code == 422
