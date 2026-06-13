"""Tests for the OpenWeatherMap client.

Covers HTTP status translation, transport failures, and — importantly — the
3-hour-interval → daily-summary aggregation logic. Uses respx to mock httpx at
the transport layer, so there is no real network traffic.
"""

from datetime import date

import httpx
import pytest
import respx

from app.core.exceptions import (
    CityNotFoundError,
    WeatherProviderTimeoutError,
    WeatherProviderUnavailableError,
)
from app.weather.openweather_client import OpenWeatherMapClient

_WEATHER_ROUTE = r"https://api\.openweathermap\.org/data/2\.5/weather"
_FORECAST_ROUTE = r"https://api\.openweathermap\.org/data/2\.5/forecast"

_CURRENT_JSON = {
    "name": "Zagreb",
    "sys": {"country": "HR"},
    "coord": {"lat": 45.8, "lon": 15.97},
    "timezone": 7200,
    "dt": 1749470400,
    "weather": [{"main": "Clouds", "description": "scattered clouds", "icon": "03d"}],
    "main": {"temp": 18.5, "feels_like": 17.8, "humidity": 65, "pressure": 1015},
    "wind": {"speed": 3.2, "deg": 180},
    "clouds": {"all": 40},
    "visibility": 10000,
}

_FORECAST_JSON = {
    "list": [
        {
            "dt_txt": "2026-06-09 09:00:00",
            "main": {"temp": 16.0, "humidity": 60},
            "weather": [{"main": "Clouds", "description": "scattered clouds", "icon": "03d"}],
            "wind": {"speed": 3.0},
            "pop": 0.1,
        },
        {
            "dt_txt": "2026-06-09 12:00:00",
            "main": {"temp": 22.0, "humidity": 55},
            "weather": [{"main": "Clear", "description": "clear sky", "icon": "01d"}],
            "wind": {"speed": 2.5},
            "pop": 0.2,
        },
        {
            "dt_txt": "2026-06-09 15:00:00",
            "main": {"temp": 20.0, "humidity": 58},
            "weather": [{"main": "Clouds", "description": "broken clouds", "icon": "04d"}],
            "wind": {"speed": 2.0},
            "pop": 0.05,
        },
        {
            "dt_txt": "2026-06-10 12:00:00",
            "main": {"temp": 24.0, "humidity": 50},
            "weather": [{"main": "Clear", "description": "clear sky", "icon": "01d"}],
            "wind": {"speed": 2.0},
            "pop": 0.0,
        },
    ]
}


async def _fetch(include_forecast: bool):
    async with httpx.AsyncClient() as http:
        client = OpenWeatherMapClient(http_client=http, api_key="test-key")
        return await client.fetch("Zagreb", include_forecast=include_forecast)


# ---------- Success + aggregation ----------


@respx.mock
async def test_fetch_current_only_skips_forecast_call() -> None:
    weather_route = respx.get(url__regex=_WEATHER_ROUTE).mock(
        return_value=httpx.Response(200, json=_CURRENT_JSON)
    )
    forecast_route = respx.get(url__regex=_FORECAST_ROUTE)

    snapshot = await _fetch(include_forecast=False)

    assert weather_route.called
    assert not forecast_route.called
    assert snapshot.city == "Zagreb"
    assert snapshot.country_code == "HR"
    assert snapshot.current.temperature_c == 18.5
    assert snapshot.forecast == ()


@respx.mock
async def test_fetch_aggregates_forecast_intervals_into_days() -> None:
    respx.get(url__regex=_WEATHER_ROUTE).mock(return_value=httpx.Response(200, json=_CURRENT_JSON))
    respx.get(url__regex=_FORECAST_ROUTE).mock(
        return_value=httpx.Response(200, json=_FORECAST_JSON)
    )

    snapshot = await _fetch(include_forecast=True)

    assert len(snapshot.forecast) == 2
    day1 = snapshot.forecast[0]
    assert day1.date == date(2026, 6, 9)
    assert day1.temp_min_c == 16.0
    assert day1.temp_max_c == 22.0
    assert day1.avg_humidity_pct == 58  # mean(60, 55, 58) rounded
    assert day1.chance_of_rain_pct == 20  # max pop (0.2) * 100
    assert day1.dominant_condition == "Clouds"  # 2 Clouds vs 1 Clear
    assert day1.description == "clear sky"  # midday (12:00) interval wins
    assert day1.wind_speed_mps_avg == 2.5  # mean(3.0, 2.5, 2.0)


@respx.mock
async def test_empty_forecast_list_yields_no_days() -> None:
    respx.get(url__regex=_WEATHER_ROUTE).mock(return_value=httpx.Response(200, json=_CURRENT_JSON))
    respx.get(url__regex=_FORECAST_ROUTE).mock(return_value=httpx.Response(200, json={"list": []}))

    snapshot = await _fetch(include_forecast=True)

    assert snapshot.forecast == ()


@respx.mock
async def test_aggregation_falls_back_to_middle_interval_without_midday() -> None:
    no_midday = {
        "list": [
            {
                "dt_txt": "2026-06-09 06:00:00",
                "main": {"temp": 14.0, "humidity": 70},
                "weather": [{"main": "Rain", "description": "light rain", "icon": "10d"}],
                "wind": {"speed": 1.0},
                "pop": 0.6,
            },
            {
                "dt_txt": "2026-06-09 18:00:00",
                "main": {"temp": 19.0, "humidity": 65},
                "weather": [{"main": "Clouds", "description": "overcast clouds", "icon": "04d"}],
                "wind": {"speed": 1.5},
                "pop": 0.3,
            },
        ]
    }
    respx.get(url__regex=_WEATHER_ROUTE).mock(return_value=httpx.Response(200, json=_CURRENT_JSON))
    respx.get(url__regex=_FORECAST_ROUTE).mock(return_value=httpx.Response(200, json=no_midday))

    snapshot = await _fetch(include_forecast=True)

    assert snapshot.forecast[0].chance_of_rain_pct == 60
    # No interval between 11:00-14:00 → falls back to the middle interval.
    assert snapshot.forecast[0].description == "overcast clouds"


# ---------- HTTP status translation ----------


@respx.mock
async def test_404_raises_city_not_found() -> None:
    respx.get(url__regex=_WEATHER_ROUTE).mock(
        return_value=httpx.Response(404, json={"message": "city not found"})
    )

    with pytest.raises(CityNotFoundError):
        await _fetch(include_forecast=False)


@respx.mock
async def test_401_raises_unavailable() -> None:
    respx.get(url__regex=_WEATHER_ROUTE).mock(return_value=httpx.Response(401))

    with pytest.raises(WeatherProviderUnavailableError):
        await _fetch(include_forecast=False)


@respx.mock
async def test_500_raises_unavailable() -> None:
    respx.get(url__regex=_WEATHER_ROUTE).mock(return_value=httpx.Response(503))

    with pytest.raises(WeatherProviderUnavailableError):
        await _fetch(include_forecast=False)


@respx.mock
async def test_unexpected_status_raises_unavailable() -> None:
    respx.get(url__regex=_WEATHER_ROUTE).mock(return_value=httpx.Response(418))

    with pytest.raises(WeatherProviderUnavailableError):
        await _fetch(include_forecast=False)


# ---------- Transport failures ----------


@respx.mock
async def test_timeout_raises_timeout_error() -> None:
    respx.get(url__regex=_WEATHER_ROUTE).mock(side_effect=httpx.ConnectTimeout("timed out"))

    with pytest.raises(WeatherProviderTimeoutError):
        await _fetch(include_forecast=False)


@respx.mock
async def test_connection_error_raises_unavailable() -> None:
    respx.get(url__regex=_WEATHER_ROUTE).mock(side_effect=httpx.ConnectError("connection refused"))

    with pytest.raises(WeatherProviderUnavailableError):
        await _fetch(include_forecast=False)
