"""LLM prompt templates, centralized so they're versioned and reviewable."""

from app.recommendations.models import DailyRecommendation
from app.weather.models import ForecastDay, WeatherSnapshot

SYSTEM_PROMPT = """You are a personal weather assistant providing concise, practical recommendations.

Your responses must:
- Be specific and actionable, not generic
- Account for local context when relevant (city, culture, season)
- Balance practicality with personality — friendly but not overly chatty
- Always return valid JSON matching the requested schema
- Use the exact field names specified

Never invent weather details not present in the data. Never include disclaimers about being an AI."""


FOLLOWUP_SYSTEM_PROMPT = """You are a personal weather assistant answering a follow-up question.

Reply in plain, conversational prose — 2 to 4 sentences. Be specific and practical.
Do NOT output JSON, code blocks, bullet lists, or field names; just answer naturally.
Never invent weather details not present in the data. Never include disclaimers about being an AI."""


RECOMMENDATION_SCHEMA = """{
  "summary": "Brief one-sentence summary of the day",
  "clothing": {
    "items": ["specific item 1", "specific item 2", ...],
    "reasoning": "Why these items match today's conditions"
  },
  "activities": {
    "suggested": ["activity 1", "activity 2", ...],
    "avoid": ["activity to skip", ...],
    "reasoning": "Why these choices fit the weather"
  },
  "health_tips": [
    {"tip": "specific tip", "priority": "high|medium|low"}
  ],
  "weekly_advice": "Multi-day planning note if forecast is provided, else null"
}"""


def build_recommendation_prompt(weather: WeatherSnapshot, target_date_iso: str) -> str:
    """Build the user prompt for initial recommendation generation.

    When the target date is a future day covered by the forecast, that day's
    forecast is the primary signal and today's live conditions are passed only
    as reference — otherwise the model would advise for the wrong day.
    """
    current = weather.current
    forecast_section = (
        _format_forecast(weather) if weather.forecast else "No multi-day forecast available."
    )

    target_day = _find_forecast_day(weather, target_date_iso)
    if target_day is not None:
        target_section = (
            f"TARGET DAY ({target_date_iso}) — base your recommendations on this:\n"
            f"- Temperature: {target_day.temp_min_c:.1f}-{target_day.temp_max_c:.1f}°C\n"
            f"- Condition: {target_day.description}\n"
            f"- Chance of rain: {target_day.chance_of_rain_pct}%\n"
            f"- Humidity: {target_day.avg_humidity_pct}%\n"
            f"- Wind: {target_day.wind_speed_mps_avg:.1f} m/s\n\n"
            f"TODAY'S LIVE CONDITIONS (reference only):\n"
        )
    else:
        target_section = "CURRENT CONDITIONS — base your recommendations on this:\n"

    return f"""Analyze this weather data for {weather.city}, {weather.country_code} on {target_date_iso}:

{target_section}- Temperature: {current.temperature_c:.1f}°C (feels like {current.feels_like_c:.1f}°C)
- Condition: {current.description}
- Humidity: {current.humidity_pct}%
- Wind: {current.wind_speed_mps:.1f} m/s
- Cloudiness: {current.cloudiness_pct}%

{forecast_section}

Provide recommendations as JSON matching exactly this schema:
{RECOMMENDATION_SCHEMA}

Be specific and practical. If a 5-day forecast is provided, include weekly_advice
highlighting the best day for outdoor activities and any preparation needed for
weather changes. If no forecast, set weekly_advice to null."""


def _find_forecast_day(weather: WeatherSnapshot, target_date_iso: str) -> ForecastDay | None:
    """Return the forecast entry whose date matches target_date_iso, if any."""
    return next(
        (day for day in weather.forecast if day.date.isoformat() == target_date_iso),
        None,
    )


def build_followup_prompt(
    weather: WeatherSnapshot,
    previous: DailyRecommendation,
    question: str,
) -> str:
    """Build the user prompt for a follow-up question with context."""
    return f"""Previous context:
City: {weather.city}, {weather.country_code}
Current weather: {weather.current.description}, {weather.current.temperature_c:.1f}°C
Previous recommendation summary: {previous.summary}
Previous clothing advice: {", ".join(previous.clothing.items)}
Previous suggested activities: {", ".join(previous.activities.suggested)}

User's follow-up question: {question}

Provide a concise, helpful answer (2-4 sentences). Reference the previous recommendations
when relevant. If the question is unrelated to weather/activities/clothing, gently steer back."""


def _format_forecast(weather: WeatherSnapshot) -> str:
    """Render forecast days as bullet list."""
    lines = ["5-DAY FORECAST:"]
    for day in weather.forecast:
        lines.append(
            f"- {day.date.isoformat()}: "
            f"{day.temp_min_c:.1f}-{day.temp_max_c:.1f}°C, "
            f"{day.description}, "
            f"{day.chance_of_rain_pct}% rain chance, "
            f"humidity {day.avg_humidity_pct}%"
        )
    return "\n".join(lines)
