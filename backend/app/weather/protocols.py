"""Protocol for weather data providers."""

from typing import Protocol, runtime_checkable

from app.weather.models import WeatherSnapshot


@runtime_checkable
class IWeatherProvider(Protocol):
    """Contract for any weather data provider.

    The service depends on this Protocol rather than a concrete client, so
    OpenWeatherMap can be swapped for another provider (or a fake in tests)
    without touching the service layer.
    """

    async def fetch(self, city: str, include_forecast: bool = True) -> WeatherSnapshot:
        """Fetch current weather and optional forecast for the given city.

        Args:
            city: City name, optionally with a country code.
            include_forecast: Whether to include the 5-day forecast.

        Returns:
            A ``WeatherSnapshot`` for the city.

        Raises:
            CityNotFoundError: The city cannot be resolved.
            WeatherProviderUnavailableError: Upstream 5xx or other failure.
            WeatherProviderTimeoutError: The request times out.
        """
        ...
