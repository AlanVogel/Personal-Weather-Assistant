"""OpenWeatherMap implementation of the weather provider Protocol."""

import asyncio
from collections import defaultdict
from collections.abc import Iterable
from datetime import UTC, datetime
from statistics import mean
from typing import Any, cast

import httpx

from app.core.exceptions import (
    CityNotFoundError,
    WeatherProviderTimeoutError,
    WeatherProviderUnavailableError,
)
from app.core.logging import get_logger
from app.weather.models import CurrentConditions, ForecastDay, WeatherSnapshot

logger = get_logger(__name__)

_BASE_URL = "https://api.openweathermap.org/data/2.5"


class OpenWeatherMapClient:
    """OpenWeatherMap API client implementing the ``IWeatherProvider`` Protocol.

    Owns HTTP communication via a shared async httpx client, concurrency
    limiting via a semaphore, provider-error translation to domain exceptions,
    and aggregation of OpenWeatherMap's 3-hour forecast intervals into daily
    summaries. The httpx client is injected (not owned) so its connection pool
    is reused across requests.
    """

    def __init__(
        self,
        http_client: httpx.AsyncClient,
        api_key: str,
        units: str = "metric",
        semaphore: asyncio.Semaphore | None = None,
    ) -> None:
        self._http = http_client
        self._api_key = api_key
        self._units = units
        self._semaphore = semaphore or asyncio.Semaphore(20)

    async def fetch(self, city: str, include_forecast: bool = True) -> WeatherSnapshot:
        """Fetch current weather and, optionally, the 5-day forecast.

        When the forecast is requested, the current and forecast calls run
        concurrently to cut wall-clock latency.

        Args:
            city: City name, optionally with a country code (e.g. "London,UK").
            include_forecast: Whether to also fetch and aggregate the forecast.

        Returns:
            A ``WeatherSnapshot`` with current conditions and (if requested)
            daily forecast entries.

        Raises:
            CityNotFoundError: The provider could not resolve the city (404).
            WeatherProviderTimeoutError: The provider did not respond in time.
            WeatherProviderUnavailableError: Auth failure, 5xx, or other
                non-200 response from the provider.
        """
        async with self._semaphore:
            if include_forecast:
                current_task = self._fetch_current(city)
                forecast_task = self._fetch_forecast(city)
                current_raw, forecast_raw = await asyncio.gather(
                    current_task, forecast_task, return_exceptions=False
                )
            else:
                current_raw = await self._fetch_current(city)
                forecast_raw = None

            return self._build_snapshot(current_raw, forecast_raw)

    async def _fetch_current(self, city: str) -> dict[str, Any]:
        return await self._request(
            "/weather", params={"q": city, "appid": self._api_key, "units": self._units}
        )

    async def _fetch_forecast(self, city: str) -> dict[str, Any]:
        return await self._request(
            "/forecast", params={"q": city, "appid": self._api_key, "units": self._units}
        )

    async def _request(self, path: str, params: dict[str, str]) -> dict[str, Any]:
        url = f"{_BASE_URL}{path}"
        try:
            response = await self._http.get(url, params=params)
        except httpx.TimeoutException as exc:
            logger.warning("openweather_timeout", path=path, error=str(exc))
            raise WeatherProviderTimeoutError() from exc
        except httpx.HTTPError as exc:
            logger.error("openweather_network_error", path=path, error=str(exc))
            raise WeatherProviderUnavailableError() from exc

        if response.status_code == 404:
            city = params.get("q", "unknown")
            raise CityNotFoundError(f"City '{city}' could not be found")
        if response.status_code == 401:
            logger.error("openweather_unauthorized")
            raise WeatherProviderUnavailableError("Weather provider authentication failed")
        if response.status_code >= 500:
            logger.warning(
                "openweather_server_error",
                status_code=response.status_code,
                path=path,
            )
            raise WeatherProviderUnavailableError()
        if response.status_code != 200:
            logger.warning(
                "openweather_unexpected_status",
                status_code=response.status_code,
                path=path,
            )
            raise WeatherProviderUnavailableError()

        return cast(dict[str, Any], response.json())

    def _build_snapshot(
        self,
        current_raw: dict[str, Any],
        forecast_raw: dict[str, Any] | None,
    ) -> WeatherSnapshot:
        """Translate raw provider responses into our domain model."""
        current = self._parse_current(current_raw)
        forecast = self._parse_forecast(forecast_raw) if forecast_raw else ()

        return WeatherSnapshot(
            city=current_raw["name"],
            country_code=current_raw["sys"]["country"],
            latitude=current_raw["coord"]["lat"],
            longitude=current_raw["coord"]["lon"],
            timezone_offset_seconds=current_raw.get("timezone", 0),
            current=current,
            forecast=forecast,
        )

    @staticmethod
    def _parse_current(raw: dict[str, Any]) -> CurrentConditions:
        weather = raw["weather"][0]
        main = raw["main"]
        wind = raw.get("wind", {})

        return CurrentConditions(
            temperature_c=main["temp"],
            feels_like_c=main["feels_like"],
            humidity_pct=main["humidity"],
            pressure_hpa=main["pressure"],
            wind_speed_mps=wind.get("speed", 0.0),
            wind_direction_deg=wind.get("deg"),
            cloudiness_pct=raw.get("clouds", {}).get("all", 0),
            visibility_m=raw.get("visibility"),
            condition=weather["main"],
            description=weather["description"],
            icon_code=weather["icon"],
            observed_at=datetime.fromtimestamp(raw["dt"], tz=UTC),
        )

    @staticmethod
    def _parse_forecast(raw: dict[str, Any]) -> tuple[ForecastDay, ...]:
        """Aggregate 3-hour intervals into daily summaries.

        OpenWeatherMap returns 40 intervals (5 days × 8/day). We group by date,
        compute min/max temp, average humidity, dominant condition, max precip.
        """
        intervals = raw.get("list", [])
        if not intervals:
            return ()

        by_date: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for interval in intervals:
            day_key = interval["dt_txt"].split(" ")[0]
            by_date[day_key].append(interval)

        days: list[ForecastDay] = []
        for day_key in sorted(by_date.keys()):
            day_intervals = by_date[day_key]
            days.append(_aggregate_day(day_key, day_intervals))

        return tuple(days)


def _aggregate_day(day_key: str, intervals: Iterable[dict[str, Any]]) -> ForecastDay:
    """Combine 3-hour intervals into a single day's summary."""
    intervals_list = list(intervals)
    temps = [i["main"]["temp"] for i in intervals_list]
    humidities = [i["main"]["humidity"] for i in intervals_list]
    winds = [i.get("wind", {}).get("speed", 0.0) for i in intervals_list]
    rains = [i.get("pop", 0.0) for i in intervals_list]

    # Dominant condition: most common
    conditions = [i["weather"][0]["main"] for i in intervals_list]
    dominant = max(set(conditions), key=conditions.count)

    # Description and icon from the midday interval, if available
    midday = _find_midday_interval(intervals_list) or intervals_list[len(intervals_list) // 2]

    return ForecastDay(
        date=datetime.strptime(day_key, "%Y-%m-%d").date(),
        temp_min_c=min(temps),
        temp_max_c=max(temps),
        avg_humidity_pct=round(mean(humidities)),
        chance_of_rain_pct=round(max(rains) * 100),
        dominant_condition=dominant,
        description=midday["weather"][0]["description"],
        icon_code=midday["weather"][0]["icon"],
        wind_speed_mps_avg=round(mean(winds), 2),
    )


def _find_midday_interval(intervals: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Find the interval closest to noon for representative description/icon."""
    for interval in intervals:
        hour = int(interval["dt_txt"].split(" ")[1].split(":")[0])
        if 11 <= hour <= 14:
            return interval
    return None
