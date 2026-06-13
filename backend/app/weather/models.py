"""Provider-agnostic weather domain models."""

from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class CurrentConditions(BaseModel):
    """Snapshot of current weather at a location."""

    model_config = ConfigDict(frozen=True)

    temperature_c: Annotated[float, Field(description="Temperature in Celsius")]
    feels_like_c: Annotated[float, Field(description="Apparent temperature in Celsius")]
    humidity_pct: Annotated[int, Field(ge=0, le=100)]
    pressure_hpa: int
    wind_speed_mps: Annotated[float, Field(ge=0)]
    wind_direction_deg: Annotated[int, Field(ge=0, le=360)] | None = None
    cloudiness_pct: Annotated[int, Field(ge=0, le=100)]
    visibility_m: int | None = None
    condition: str = Field(description="Short condition name, e.g. 'Rain'")
    description: str = Field(description="Human-readable description")
    icon_code: str = Field(description="Icon identifier from provider")
    observed_at: datetime


class ForecastDay(BaseModel):
    """Aggregated forecast for a single day."""

    model_config = ConfigDict(frozen=True)

    date: date
    temp_min_c: float
    temp_max_c: float
    avg_humidity_pct: Annotated[int, Field(ge=0, le=100)]
    chance_of_rain_pct: Annotated[int, Field(ge=0, le=100)]
    dominant_condition: str
    description: str
    icon_code: str
    wind_speed_mps_avg: Annotated[float, Field(ge=0)]


class WeatherSnapshot(BaseModel):
    """Complete weather data for a location: current + multi-day forecast."""

    model_config = ConfigDict(frozen=True)

    city: str
    country_code: str
    latitude: float
    longitude: float
    timezone_offset_seconds: int
    current: CurrentConditions
    forecast: tuple[ForecastDay, ...] = ()

    def forecast_for(self, target: date) -> ForecastDay | None:
        """Return the forecast entry for a specific date, or None if unavailable."""
        return next((day for day in self.forecast if day.date == target), None)
