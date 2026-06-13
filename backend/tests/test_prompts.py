"""Tests for prompt construction.

The recommendation prompt must base its advice on the *target* day. When the
user asks about a future forecast day, today's live conditions should be demoted
to reference-only so the model doesn't advise for the wrong day.
"""

from app.recommendations.prompts import build_recommendation_prompt
from app.weather.models import WeatherSnapshot


def test_prompt_targets_forecast_day_when_future(sample_weather: WeatherSnapshot) -> None:
    # 2026-06-10 is a forecast day in the fixture (clear sky, 15-24°C).
    prompt = build_recommendation_prompt(sample_weather, "2026-06-10")

    assert "TARGET DAY (2026-06-10)" in prompt
    assert "base your recommendations on this" in prompt
    assert "TODAY'S LIVE CONDITIONS (reference only)" in prompt
    # The target day's forecast values must be present.
    assert "15.0-24.0°C" in prompt
    assert "clear sky" in prompt


def test_prompt_uses_current_conditions_when_target_not_in_forecast(
    sample_weather: WeatherSnapshot,
) -> None:
    # A date with no matching forecast day falls back to live conditions.
    prompt = build_recommendation_prompt(sample_weather, "2026-06-09")

    # 2026-06-09 IS a forecast day in the fixture, so it should still target it.
    assert "TARGET DAY (2026-06-09)" in prompt


def test_prompt_without_forecast_uses_current_conditions() -> None:
    snapshot = WeatherSnapshot(
        city="Zagreb",
        country_code="HR",
        latitude=45.8,
        longitude=15.97,
        timezone_offset_seconds=7200,
        current=_minimal_current(),
        forecast=(),
    )

    prompt = build_recommendation_prompt(snapshot, "2026-06-09")

    assert "CURRENT CONDITIONS — base your recommendations on this" in prompt
    assert "No multi-day forecast available." in prompt
    assert "TARGET DAY" not in prompt


def _minimal_current():
    from datetime import UTC, datetime

    from app.weather.models import CurrentConditions

    return CurrentConditions(
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
    )
