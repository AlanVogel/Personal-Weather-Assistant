"""LLM output-quality evaluation and prompt-regression tests.

Two layers:

1. **Offline (always runs):** sanity-checks the evaluator and asserts the prompt
   builder still carries each scenario's weather signals. These are deterministic
   and protect against silent prompt regressions in CI.
2. **Live (opt-in):** calls the real Groq model for each golden scenario and
   asserts the response hits the expected advice. Skipped automatically unless a
   real ``GROQ_API_KEY`` (``gsk_...``) is set, so CI stays offline. Run locally
   or in a nightly job with ``pytest -m llm_eval``.
"""

import os

import pytest
from groq import AsyncGroq

from app.core.config import get_settings
from app.recommendations.groq_generator import GroqRecommendationGenerator
from app.recommendations.models import (
    ActivityAdvice,
    ClothingAdvice,
    DailyRecommendation,
    HealthTip,
    Priority,
)
from app.recommendations.prompts import build_recommendation_prompt

from .eval.evaluator import evaluate, flatten_recommendation_text
from .eval.scenarios import ALL_SCENARIOS, COLD_AND_RAINY, HOT_AND_SUNNY, WeatherScenario

_HAS_REAL_KEY = os.environ.get("GROQ_API_KEY", "").startswith("gsk_")


# ---------- Offline: evaluator sanity ----------


def _rec(*, summary: str, items: list[str], reasoning: str) -> DailyRecommendation:
    return DailyRecommendation(
        summary=summary,
        clothing=ClothingAdvice(items=items, reasoning=reasoning),
        activities=ActivityAdvice(
            suggested=["stay in"], reasoning="Weather is not great for going out."
        ),
        health_tips=[HealthTip(tip="Keep dry and warm today.", priority=Priority.MEDIUM)],
    )


def test_evaluator_passes_a_good_cold_rainy_recommendation() -> None:
    good = _rec(
        summary="Cold and wet — bundle up and bring rain protection.",
        items=["waterproof jacket", "warm coat", "umbrella", "gloves"],
        reasoning="Near-freezing rain calls for warm, waterproof layers.",
    )
    result = evaluate(good, COLD_AND_RAINY)
    assert result.passed
    assert result.score == 1.0


def test_evaluator_fails_an_inappropriate_recommendation() -> None:
    bad = _rec(
        summary="Lovely day out!",
        items=["t-shirt", "shorts", "sandals"],
        reasoning="Perfect for the beach.",
    )
    result = evaluate(bad, COLD_AND_RAINY)
    assert not result.passed
    assert result.missing  # reports which keyword groups were missed


def test_flatten_includes_all_text_fields() -> None:
    rec = _rec(summary="alpha summary line", items=["beta item"], reasoning="gamma reasoning here")
    text = flatten_recommendation_text(rec)
    assert "beta item" in text and "gamma reasoning" in text and "alpha summary" in text


# ---------- Offline: prompt regression ----------


@pytest.mark.parametrize("scenario", ALL_SCENARIOS, ids=lambda s: s.name)
def test_prompt_carries_weather_signals(scenario: WeatherScenario) -> None:
    prompt = build_recommendation_prompt(scenario.weather, scenario.target_date_iso)
    current = scenario.weather.current
    assert scenario.weather.city in prompt
    assert current.description in prompt
    assert f"{current.temperature_c:.1f}" in prompt


def test_rainy_prompt_differs_from_sunny_prompt() -> None:
    rainy = build_recommendation_prompt(COLD_AND_RAINY.weather, COLD_AND_RAINY.target_date_iso)
    sunny = build_recommendation_prompt(HOT_AND_SUNNY.weather, HOT_AND_SUNNY.target_date_iso)
    assert "moderate rain" in rainy
    assert "clear sky" in sunny
    assert rainy != sunny


# ---------- Live: real-model evaluation (opt-in) ----------


@pytest.mark.llm_eval
@pytest.mark.skipif(not _HAS_REAL_KEY, reason="requires a real GROQ_API_KEY (gsk_...)")
@pytest.mark.parametrize("scenario", ALL_SCENARIOS, ids=lambda s: s.name)
async def test_live_recommendation_quality(scenario: WeatherScenario) -> None:
    settings = get_settings()
    client = AsyncGroq(api_key=settings.groq_api_key, timeout=settings.llm_timeout_seconds)
    generator = GroqRecommendationGenerator(
        client=client,
        model=settings.groq_model,
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
    )

    rec = await generator.generate(scenario.weather, scenario.target_date_iso)
    result = evaluate(rec, scenario)

    assert result.passed, (
        f"{scenario.name}: expected advice missing {result.missing} (score={result.score:.2f})"
    )
