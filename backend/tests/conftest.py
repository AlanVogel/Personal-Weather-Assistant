"""Pytest fixtures and Fake implementations.

Tests use FakeWeatherProvider and FakeRecommendationGenerator instead of
mocking. This is cleaner — duck-typed implementations of the Protocols.
Tests run offline, no API keys needed.
"""

import os

# Disable per-IP rate limiting before the app (and its cached settings) load,
# so accumulated test calls to the LLM endpoints don't trip the limiter.
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")

from collections.abc import AsyncGenerator
from datetime import UTC, date, datetime

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.dependencies import (
    LifespanClients,
    get_recommendation_generator,
    get_weather_provider,
)
from app.main import create_app
from app.recommendations.models import (
    ActivityAdvice,
    ClothingAdvice,
    DailyRecommendation,
    FollowUpAnswer,
    HealthTip,
    Priority,
)
from app.weather.cache import WeatherCache
from app.weather.models import CurrentConditions, ForecastDay, WeatherSnapshot

# ---------- Fixtures: data ----------


@pytest.fixture
def sample_weather() -> WeatherSnapshot:
    """Realistic sample weather snapshot for tests."""
    return WeatherSnapshot(
        city="Zagreb",
        country_code="HR",
        latitude=45.8,
        longitude=15.97,
        timezone_offset_seconds=7200,
        current=CurrentConditions(
            temperature_c=18.5,
            feels_like_c=17.8,
            humidity_pct=65,
            pressure_hpa=1015,
            wind_speed_mps=3.2,
            wind_direction_deg=180,
            cloudiness_pct=40,
            visibility_m=10000,
            condition="Clouds",
            description="scattered clouds",
            icon_code="03d",
            observed_at=datetime(2026, 6, 9, 12, 0, tzinfo=UTC),
        ),
        forecast=(
            ForecastDay(
                date=date(2026, 6, 9),
                temp_min_c=14.0,
                temp_max_c=22.0,
                avg_humidity_pct=60,
                chance_of_rain_pct=10,
                dominant_condition="Clouds",
                description="scattered clouds",
                icon_code="03d",
                wind_speed_mps_avg=3.0,
            ),
            ForecastDay(
                date=date(2026, 6, 10),
                temp_min_c=15.0,
                temp_max_c=24.0,
                avg_humidity_pct=55,
                chance_of_rain_pct=5,
                dominant_condition="Clear",
                description="clear sky",
                icon_code="01d",
                wind_speed_mps_avg=2.5,
            ),
        ),
    )


@pytest.fixture
def sample_recommendation() -> DailyRecommendation:
    """Realistic sample recommendation for tests."""
    return DailyRecommendation(
        summary="Mild June day with scattered clouds — comfortable for most outdoor activities.",
        clothing=ClothingAdvice(
            items=["light jacket", "long-sleeve shirt", "jeans", "sneakers"],
            reasoning="Temperatures around 18°C feel pleasant but a light layer is wise.",
        ),
        activities=ActivityAdvice(
            suggested=["walk in Maksimir", "outdoor coffee", "cycling on Sava"],
            avoid=["beach trip"],
            reasoning="Cloudy with mild temperatures — perfect for active outdoor time.",
        ),
        health_tips=[
            HealthTip(
                tip="UV is moderate even with clouds — sunscreen recommended",
                priority=Priority.MEDIUM,
            ),
        ],
        weekly_advice="Tomorrow will be sunnier and warmer — best day for a longer outing.",
    )


# ---------- Fakes: implementations of Protocols ----------


class FakeWeatherProvider:
    """In-memory weather provider for tests. Implements IWeatherProvider."""

    def __init__(self, snapshot: WeatherSnapshot, fail_with: Exception | None = None) -> None:
        self._snapshot = snapshot
        self._fail_with = fail_with
        self.calls: list[tuple[str, bool]] = []

    async def fetch(self, city: str, include_forecast: bool = True) -> WeatherSnapshot:
        self.calls.append((city, include_forecast))
        if self._fail_with:
            raise self._fail_with
        return self._snapshot


class FakeRecommendationGenerator:
    """In-memory generator for tests. Implements IRecommendationGenerator."""

    def __init__(
        self,
        recommendation: DailyRecommendation,
        followup_answer: str = "That sounds great!",
        fail_with: Exception | None = None,
    ) -> None:
        self._recommendation = recommendation
        self._followup = followup_answer
        self._fail_with = fail_with
        self.generate_calls: list[tuple[str, str]] = []
        self.followup_calls: list[tuple[str, str]] = []

    async def generate(self, weather: WeatherSnapshot, target_date_iso: str) -> DailyRecommendation:
        self.generate_calls.append((weather.city, target_date_iso))
        if self._fail_with:
            raise self._fail_with
        return self._recommendation

    async def follow_up(
        self,
        weather: WeatherSnapshot,
        previous_recommendation: DailyRecommendation,
        user_question: str,
    ) -> FollowUpAnswer:
        self.followup_calls.append((weather.city, user_question))
        if self._fail_with:
            raise self._fail_with
        return FollowUpAnswer(answer=self._followup)


# ---------- App fixture with fakes ----------


@pytest_asyncio.fixture
async def app_with_fakes(
    sample_weather: WeatherSnapshot,
    sample_recommendation: DailyRecommendation,
) -> AsyncGenerator[tuple[FastAPI, FakeWeatherProvider, FakeRecommendationGenerator], None]:
    """Create app with Fake implementations of the Protocols injected."""
    app = create_app()

    fake_weather = FakeWeatherProvider(sample_weather)
    fake_generator = FakeRecommendationGenerator(sample_recommendation)

    # Override dependencies
    app.dependency_overrides[get_weather_provider] = lambda: fake_weather
    app.dependency_overrides[get_recommendation_generator] = lambda: fake_generator

    # Bypass lifespan — set minimal state directly
    import asyncio

    import httpx
    from groq import AsyncGroq

    app.state.clients = LifespanClients(
        http_client=httpx.AsyncClient(),
        groq_client=AsyncGroq(api_key="test"),
        weather_cache=WeatherCache(ttl_seconds=60),
        llm_semaphore=asyncio.Semaphore(10),
        weather_semaphore=asyncio.Semaphore(20),
    )

    yield app, fake_weather, fake_generator

    await app.state.clients.http_client.aclose()
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client(
    app_with_fakes: tuple[FastAPI, FakeWeatherProvider, FakeRecommendationGenerator],
) -> AsyncGenerator[AsyncClient, None]:
    """HTTP client for API tests."""
    app, _, _ = app_with_fakes
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
