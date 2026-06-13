"""Tests for WeatherService — orchestration of provider + cache."""

import pytest

from app.core.exceptions import CityNotFoundError, WeatherProviderUnavailableError
from app.weather.cache import WeatherCache
from app.weather.models import WeatherSnapshot
from app.weather.service import WeatherService
from tests.conftest import FakeWeatherProvider


class TestWeatherService:
    async def test_get_weather_returns_snapshot(self, sample_weather: WeatherSnapshot) -> None:
        provider = FakeWeatherProvider(sample_weather)
        cache = WeatherCache(ttl_seconds=60)
        service = WeatherService(provider=provider, cache=cache)

        result = await service.get_weather("Zagreb")
        assert result.city == "Zagreb"

    async def test_get_weather_caches_result(self, sample_weather: WeatherSnapshot) -> None:
        provider = FakeWeatherProvider(sample_weather)
        cache = WeatherCache(ttl_seconds=60)
        service = WeatherService(provider=provider, cache=cache)

        await service.get_weather("Zagreb")
        await service.get_weather("Zagreb")

        # Provider called only once thanks to cache
        assert len(provider.calls) == 1

    async def test_different_cities_separate_cache(self, sample_weather: WeatherSnapshot) -> None:
        provider = FakeWeatherProvider(sample_weather)
        cache = WeatherCache(ttl_seconds=60)
        service = WeatherService(provider=provider, cache=cache)

        await service.get_weather("Zagreb")
        await service.get_weather("London")

        assert len(provider.calls) == 2

    async def test_include_forecast_flag_separates_cache(
        self, sample_weather: WeatherSnapshot
    ) -> None:
        provider = FakeWeatherProvider(sample_weather)
        cache = WeatherCache(ttl_seconds=60)
        service = WeatherService(provider=provider, cache=cache)

        await service.get_weather("Zagreb", include_forecast=False)
        await service.get_weather("Zagreb", include_forecast=True)

        # Different cache keys
        assert len(provider.calls) == 2

    async def test_city_case_insensitive(self, sample_weather: WeatherSnapshot) -> None:
        provider = FakeWeatherProvider(sample_weather)
        cache = WeatherCache(ttl_seconds=60)
        service = WeatherService(provider=provider, cache=cache)

        await service.get_weather("Zagreb")
        await service.get_weather("zagreb")
        await service.get_weather("ZAGREB")

        # All normalized to same cache key
        assert len(provider.calls) == 1

    async def test_provider_error_propagates(self, sample_weather: WeatherSnapshot) -> None:
        provider = FakeWeatherProvider(sample_weather, fail_with=CityNotFoundError("not found"))
        cache = WeatherCache(ttl_seconds=60)
        service = WeatherService(provider=provider, cache=cache)

        with pytest.raises(CityNotFoundError):
            await service.get_weather("NoSuchCity")

    async def test_provider_unavailable_propagates(self, sample_weather: WeatherSnapshot) -> None:
        provider = FakeWeatherProvider(sample_weather, fail_with=WeatherProviderUnavailableError())
        cache = WeatherCache(ttl_seconds=60)
        service = WeatherService(provider=provider, cache=cache)

        with pytest.raises(WeatherProviderUnavailableError):
            await service.get_weather("Zagreb")
