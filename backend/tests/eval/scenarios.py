"""Golden weather scenarios for evaluating recommendation quality.

Each scenario pairs a concrete ``WeatherSnapshot`` with the keyword groups a
good recommendation is expected to surface. A scenario passes when, for every
group, at least one keyword appears somewhere in the recommendation text. This
is a deliberately lightweight, deterministic proxy for output quality — not a
full faithfulness metric — so it can gate prompt changes in CI and be run
against the real model when a key is available.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.weather.models import CurrentConditions, ForecastDay, WeatherSnapshot


@dataclass(frozen=True)
class WeatherScenario:
    """A named weather input plus the keyword groups good advice should hit."""

    name: str
    weather: WeatherSnapshot
    target_date_iso: str
    # Each inner list is an OR-group: at least one of its keywords must appear.
    expected_keyword_groups: list[list[str]] = field(default_factory=list)


def _snapshot(
    *,
    temp_c: float,
    feels_like_c: float,
    humidity: int,
    wind: float,
    clouds: int,
    condition: str,
    description: str,
    forecast: tuple[ForecastDay, ...] = (),
) -> WeatherSnapshot:
    return WeatherSnapshot(
        city="Zagreb",
        country_code="HR",
        latitude=45.8,
        longitude=15.97,
        timezone_offset_seconds=7200,
        current=CurrentConditions(
            temperature_c=temp_c,
            feels_like_c=feels_like_c,
            humidity_pct=humidity,
            pressure_hpa=1013,
            wind_speed_mps=wind,
            wind_direction_deg=180,
            cloudiness_pct=clouds,
            visibility_m=10000,
            condition=condition,
            description=description,
            icon_code="01d",
            observed_at=datetime(2026, 6, 9, 12, 0, tzinfo=UTC),
        ),
        forecast=forecast,
    )


COLD_AND_RAINY = WeatherScenario(
    name="cold_and_rainy",
    weather=_snapshot(
        temp_c=3.0,
        feels_like_c=-1.0,
        humidity=92,
        wind=8.0,
        clouds=100,
        condition="Rain",
        description="moderate rain",
    ),
    target_date_iso="2026-06-09",
    expected_keyword_groups=[
        ["umbrella", "waterproof", "raincoat", "rain jacket", "rain"],
        ["coat", "warm", "jacket", "layers", "thermal", "gloves"],
    ],
)

HOT_AND_SUNNY = WeatherScenario(
    name="hot_and_sunny",
    weather=_snapshot(
        temp_c=35.0,
        feels_like_c=38.0,
        humidity=30,
        wind=1.5,
        clouds=0,
        condition="Clear",
        description="clear sky",
    ),
    target_date_iso="2026-06-09",
    expected_keyword_groups=[
        ["sunscreen", "spf", "hat", "sunglasses", "shade"],
        ["hydrate", "hydration", "water", "drink", "fluids"],
        ["light", "breathable", "shorts", "linen", "cotton"],
    ],
)

MILD_AND_CLOUDY = WeatherScenario(
    name="mild_and_cloudy",
    weather=_snapshot(
        temp_c=18.0,
        feels_like_c=17.0,
        humidity=60,
        wind=3.0,
        clouds=60,
        condition="Clouds",
        description="scattered clouds",
    ),
    target_date_iso="2026-06-09",
    expected_keyword_groups=[
        ["light jacket", "layer", "long-sleeve", "sweater", "cardigan", "jacket"],
    ],
)


ALL_SCENARIOS: list[WeatherScenario] = [COLD_AND_RAINY, HOT_AND_SUNNY, MILD_AND_CLOUDY]
