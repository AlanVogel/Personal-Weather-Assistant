"""Weather service: orchestrates provider + cache."""

from app.core.logging import get_logger
from app.weather.cache import WeatherCache
from app.weather.models import WeatherSnapshot
from app.weather.protocols import IWeatherProvider

logger = get_logger(__name__)


class WeatherService:
    """Coordinates fetching weather data with caching."""

    def __init__(self, provider: IWeatherProvider, cache: WeatherCache) -> None:
        self._provider = provider
        self._cache = cache

    async def get_weather(
        self,
        city: str,
        include_forecast: bool = True,
    ) -> WeatherSnapshot:
        """Fetch weather, serving from cache when an entry is still fresh.

        The cache key includes the forecast flag, so a current-only response is
        cached separately from a full current-plus-forecast response.

        Args:
            city: City name, optionally with a country code.
            include_forecast: Whether to include the aggregated 5-day forecast.

        Returns:
            A ``WeatherSnapshot`` for the city.

        Raises:
            CityNotFoundError, WeatherProviderTimeoutError,
            WeatherProviderUnavailableError: Propagated from the provider on a
                cache miss.
        """
        cache_key = self._build_key(city, include_forecast)
        logger.debug("weather_request", city=city, include_forecast=include_forecast)

        result = await self._cache.get_or_set(
            cache_key,
            factory=lambda: self._provider.fetch(city, include_forecast=include_forecast),
        )
        # Type narrowing: WeatherCache returns object, we know it's WeatherSnapshot
        assert isinstance(result, WeatherSnapshot)
        return result

    @staticmethod
    def _build_key(city: str, include_forecast: bool) -> str:
        normalized = city.strip().lower()
        suffix = "full" if include_forecast else "current"
        return f"weather:{normalized}:{suffix}"
