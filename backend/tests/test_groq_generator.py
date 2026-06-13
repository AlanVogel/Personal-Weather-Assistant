"""Error-path and success tests for the Groq recommendation generator.

The generator is the most failure-prone unit in the system: it talks to an
external LLM and parses free-form output. These tests exercise every branch of
the provider-error translation and the JSON parsing/validation pipeline using a
fake AsyncGroq-shaped client — no network, no API key.
"""

from types import SimpleNamespace

import httpx
import pytest
from groq import (
    APIConnectionError,
    APIError,
    APIStatusError,
    APITimeoutError,
    RateLimitError,
)

from app.core.exceptions import (
    LLMParseError,
    LLMProviderUnavailableError,
    LLMRateLimitError,
    LLMTimeoutError,
)
from app.recommendations.groq_generator import GroqRecommendationGenerator
from app.recommendations.models import DailyRecommendation, FollowUpAnswer
from app.weather.models import WeatherSnapshot

_REQUEST = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")


def _fake_client(create):
    """Build a minimal object shaped like AsyncGroq with a custom create()."""
    completions = SimpleNamespace(create=create)
    return SimpleNamespace(chat=SimpleNamespace(completions=completions))


def _response(content: str | None):
    """Build a minimal chat-completion response with one choice."""
    message = SimpleNamespace(content=content)
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def _generator(create) -> GroqRecommendationGenerator:
    return GroqRecommendationGenerator(
        client=_fake_client(create),  # type: ignore[arg-type]
        model="llama-test",
        temperature=0.3,
        max_tokens=500,
    )


def _returns(content: str | None):
    async def create(**_kwargs: object):
        return _response(content)

    return create


def _raises(exc: Exception):
    async def create(**_kwargs: object):
        raise exc

    return create


# ---------- Success paths ----------


async def test_generate_returns_validated_recommendation(
    sample_weather: WeatherSnapshot,
    sample_recommendation: DailyRecommendation,
) -> None:
    gen = _generator(_returns(sample_recommendation.model_dump_json()))

    result = await gen.generate(sample_weather, "2026-06-09")

    assert isinstance(result, DailyRecommendation)
    assert result.summary == sample_recommendation.summary


async def test_generate_parses_json_wrapped_in_markdown_fence(
    sample_weather: WeatherSnapshot,
    sample_recommendation: DailyRecommendation,
) -> None:
    fenced = f"```json\n{sample_recommendation.model_dump_json()}\n```"
    gen = _generator(_returns(fenced))

    result = await gen.generate(sample_weather, "2026-06-09")

    assert isinstance(result, DailyRecommendation)


async def test_follow_up_returns_trimmed_answer(
    sample_weather: WeatherSnapshot,
    sample_recommendation: DailyRecommendation,
) -> None:
    gen = _generator(_returns("  Cycling along the Sava sounds great today.  "))

    answer = await gen.follow_up(sample_weather, sample_recommendation, "Can I cycle?")

    assert isinstance(answer, FollowUpAnswer)
    assert answer.answer == "Cycling along the Sava sounds great today."


async def test_follow_up_strips_trailing_json_block(
    sample_weather: WeatherSnapshot,
    sample_recommendation: DailyRecommendation,
) -> None:
    # The model sometimes appends a JSON code block to a prose answer — drop it.
    raw = (
        "It stays warm and clear in the west of the city, so the earlier advice holds.\n\n"
        '```json\n{"temperature": 29.4, "clothing": ["sun hat"]}\n```'
    )
    gen = _generator(_returns(raw))

    answer = await gen.follow_up(sample_weather, sample_recommendation, "West side?")

    assert "```" not in answer.answer
    assert "json" not in answer.answer.lower()
    assert answer.answer.startswith("It stays warm and clear")


# ---------- Parsing / validation failures ----------


async def test_generate_malformed_json_raises_parse_error(
    sample_weather: WeatherSnapshot,
) -> None:
    gen = _generator(_returns("not json at all, sorry"))

    with pytest.raises(LLMParseError):
        await gen.generate(sample_weather, "2026-06-09")


async def test_generate_schema_violation_raises_parse_error(
    sample_weather: WeatherSnapshot,
) -> None:
    # Valid JSON, but missing required fields (clothing, activities).
    gen = _generator(_returns('{"summary": "too short to be valid anyway"}'))

    with pytest.raises(LLMParseError):
        await gen.generate(sample_weather, "2026-06-09")


async def test_generate_empty_content_raises_unavailable(
    sample_weather: WeatherSnapshot,
) -> None:
    gen = _generator(_returns(""))

    with pytest.raises(LLMProviderUnavailableError):
        await gen.generate(sample_weather, "2026-06-09")


async def test_generate_no_choices_raises_unavailable(
    sample_weather: WeatherSnapshot,
) -> None:
    async def create(**_kwargs: object):
        return SimpleNamespace(choices=[])

    gen = _generator(create)

    with pytest.raises(LLMProviderUnavailableError):
        await gen.generate(sample_weather, "2026-06-09")


# ---------- Provider-error translation ----------


@pytest.mark.parametrize(
    ("provider_error", "expected"),
    [
        (APITimeoutError(request=_REQUEST), LLMTimeoutError),
        (
            RateLimitError("slow down", response=httpx.Response(429, request=_REQUEST), body=None),
            LLMRateLimitError,
        ),
        (
            APIConnectionError(message="boom", request=_REQUEST),
            LLMProviderUnavailableError,
        ),
        (
            APIStatusError(
                "rate limited", response=httpx.Response(429, request=_REQUEST), body=None
            ),
            LLMRateLimitError,
        ),
        (
            APIStatusError(
                "server error", response=httpx.Response(500, request=_REQUEST), body=None
            ),
            LLMProviderUnavailableError,
        ),
        (APIError("generic", request=_REQUEST, body=None), LLMProviderUnavailableError),
    ],
)
async def test_provider_errors_are_translated(
    sample_weather: WeatherSnapshot,
    provider_error: Exception,
    expected: type[Exception],
) -> None:
    gen = _generator(_raises(provider_error))

    with pytest.raises(expected):
        await gen.generate(sample_weather, "2026-06-09")
