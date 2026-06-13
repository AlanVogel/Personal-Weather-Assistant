"""Weather API endpoints."""

from fastapi import APIRouter, Depends

from app.core.dependencies import get_weather_service
from app.weather.models import WeatherSnapshot
from app.weather.service import WeatherService

router = APIRouter(prefix="/api/weather", tags=["weather"])


@router.get("", response_model=WeatherSnapshot)
async def get_weather(
    city: str,
    include_forecast: bool = True,
    service: WeatherService = Depends(get_weather_service),
) -> WeatherSnapshot:
    """Get current weather and optional 5-day forecast for a city.

    - **city**: Name of the city (e.g., "Zagreb", "London,UK")
    - **include_forecast**: Whether to include the 5-day forecast
    """
    return await service.get_weather(city, include_forecast=include_forecast)
