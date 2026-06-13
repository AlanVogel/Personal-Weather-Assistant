"""Tests for RecommendationService — orchestrates weather + generator."""

from datetime import date, timedelta

import pytest

from app.core.exceptions import InvalidDateRangeError, LLMParseError
from app.recommendations.models import DailyRecommendation
from app.recommendations.service import RecommendationService
from app.weather.cache import WeatherCache
from app.weather.models import WeatherSnapshot
from app.weather.service import WeatherService
from tests.conftest import FakeRecommendationGenerator, FakeWeatherProvider


def _build_service(
    weather: WeatherSnapshot,
    recommendation: DailyRecommendation,
    generator_failure: Exception | None = None,
) -> tuple[RecommendationService, FakeWeatherProvider, FakeRecommendationGenerator]:
    provider = FakeWeatherProvider(weather)
    cache = WeatherCache(ttl_seconds=60)
    weather_service = WeatherService(provider=provider, cache=cache)
    generator = FakeRecommendationGenerator(recommendation, fail_with=generator_failure)
    service = RecommendationService(weather_service=weather_service, generator=generator)
    return service, provider, generator


class TestGetRecommendation:
    async def test_returns_combined_response(
        self,
        sample_weather: WeatherSnapshot,
        sample_recommendation: DailyRecommendation,
    ) -> None:
        service, _, _ = _build_service(sample_weather, sample_recommendation)
        result = await service.get_recommendation(city="Zagreb")

        assert result.weather.city == "Zagreb"
        assert result.recommendation.summary == sample_recommendation.summary
        assert result.target_date == date.today()

    async def test_uses_provided_target_date(
        self,
        sample_weather: WeatherSnapshot,
        sample_recommendation: DailyRecommendation,
    ) -> None:
        service, _, generator = _build_service(sample_weather, sample_recommendation)
        target = date.today() + timedelta(days=2)

        result = await service.get_recommendation(city="Zagreb", target_date=target)

        assert result.target_date == target
        assert generator.generate_calls[0][1] == target.isoformat()

    async def test_rejects_past_date(
        self,
        sample_weather: WeatherSnapshot,
        sample_recommendation: DailyRecommendation,
    ) -> None:
        service, _, _ = _build_service(sample_weather, sample_recommendation)

        with pytest.raises(InvalidDateRangeError, match="past"):
            await service.get_recommendation(
                city="Zagreb",
                target_date=date.today() - timedelta(days=1),
            )

    async def test_rejects_date_beyond_forecast(
        self,
        sample_weather: WeatherSnapshot,
        sample_recommendation: DailyRecommendation,
    ) -> None:
        service, _, _ = _build_service(sample_weather, sample_recommendation)

        with pytest.raises(InvalidDateRangeError, match="5 days"):
            await service.get_recommendation(
                city="Zagreb",
                target_date=date.today() + timedelta(days=10),
            )

    async def test_propagates_llm_errors(
        self,
        sample_weather: WeatherSnapshot,
        sample_recommendation: DailyRecommendation,
    ) -> None:
        service, _, _ = _build_service(
            sample_weather,
            sample_recommendation,
            generator_failure=LLMParseError("bad json"),
        )

        with pytest.raises(LLMParseError):
            await service.get_recommendation(city="Zagreb")


class TestFollowUp:
    async def test_returns_answer(
        self,
        sample_weather: WeatherSnapshot,
        sample_recommendation: DailyRecommendation,
    ) -> None:
        service, _, _ = _build_service(sample_weather, sample_recommendation)

        result = await service.ask_followup(
            city="Zagreb",
            target_date=date.today(),
            previous_recommendation=sample_recommendation,
            user_question="What about cycling?",
        )

        assert result.answer

    async def test_passes_question_to_generator(
        self,
        sample_weather: WeatherSnapshot,
        sample_recommendation: DailyRecommendation,
    ) -> None:
        service, _, generator = _build_service(sample_weather, sample_recommendation)

        await service.ask_followup(
            city="Zagreb",
            target_date=date.today(),
            previous_recommendation=sample_recommendation,
            user_question="What about running?",
        )

        assert generator.followup_calls[0] == ("Zagreb", "What about running?")
