"""Groq implementation of the recommendation generator Protocol."""

import asyncio

from groq import (
    APIConnectionError,
    APIError,
    APIStatusError,
    APITimeoutError,
    AsyncGroq,
    RateLimitError,
)
from pydantic import ValidationError

from app.core.exceptions import (
    LLMParseError,
    LLMProviderUnavailableError,
    LLMRateLimitError,
    LLMTimeoutError,
)
from app.core.logging import get_logger
from app.recommendations.models import DailyRecommendation, FollowUpAnswer
from app.recommendations.parsing import extract_first_json_object
from app.recommendations.prompts import (
    SYSTEM_PROMPT,
    build_followup_prompt,
    build_recommendation_prompt,
)
from app.weather.models import WeatherSnapshot

logger = get_logger(__name__)


class GroqRecommendationGenerator:
    """Groq LLM client implementing the ``IRecommendationGenerator`` Protocol.

    Calls the Groq chat API in JSON mode for structured output, limits
    concurrency with a semaphore, translates provider errors into domain
    exceptions, and validates the model's JSON against the response schema.
    The ``AsyncGroq`` client is injected and reused across requests.
    """

    def __init__(
        self,
        client: AsyncGroq,
        model: str,
        temperature: float,
        max_tokens: int,
        semaphore: asyncio.Semaphore | None = None,
    ) -> None:
        self._client = client
        self._model = model
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._semaphore = semaphore or asyncio.Semaphore(10)

    async def generate(
        self,
        weather: WeatherSnapshot,
        target_date_iso: str,
    ) -> DailyRecommendation:
        """Generate structured recommendations for the given weather.

        Args:
            weather: Current conditions and forecast for the city.
            target_date_iso: ISO-8601 date the advice should target.

        Returns:
            A validated ``DailyRecommendation``.

        Raises:
            LLMParseError: The model output was not valid JSON or failed schema
                validation.
            LLMRateLimitError, LLMTimeoutError, LLMProviderUnavailableError:
                Translated from the corresponding Groq API errors.
        """
        prompt = build_recommendation_prompt(weather, target_date_iso)

        raw_response = await self._chat(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            json_mode=True,
        )

        try:
            payload = extract_first_json_object(raw_response)
        except ValueError as exc:
            logger.warning("llm_parse_failed", error=str(exc), preview=raw_response[:200])
            raise LLMParseError(f"Could not parse recommendation response: {exc}") from exc

        try:
            return DailyRecommendation.model_validate(payload)
        except ValidationError as exc:
            logger.warning("llm_validation_failed", errors=exc.errors())
            raise LLMParseError(
                "Recommendation schema validation failed",
                validation_errors=exc.error_count(),
            ) from exc

    async def follow_up(
        self,
        weather: WeatherSnapshot,
        previous_recommendation: DailyRecommendation,
        user_question: str,
    ) -> FollowUpAnswer:
        """Answer a follow-up question grounded in a previous recommendation.

        Args:
            weather: Current conditions for the city, used as context.
            previous_recommendation: The recommendation the user is asking about.
            user_question: The user's free-text follow-up question.

        Returns:
            A ``FollowUpAnswer`` with a short conversational reply.

        Raises:
            LLMRateLimitError, LLMTimeoutError, LLMProviderUnavailableError:
                Translated from the corresponding Groq API errors.
        """
        prompt = build_followup_prompt(weather, previous_recommendation, user_question)

        raw_response = await self._chat(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            json_mode=False,
        )

        return FollowUpAnswer(answer=raw_response.strip())

    async def _chat(
        self,
        messages: list[dict[str, str]],
        json_mode: bool = False,
    ) -> str:
        """Send a chat completion request with proper error translation."""
        kwargs: dict[str, object] = {
            "model": self._model,
            "messages": messages,
            "temperature": self._temperature,
            "max_tokens": self._max_tokens,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        try:
            async with self._semaphore:
                response = await self._client.chat.completions.create(**kwargs)  # type: ignore[call-overload]
        except APITimeoutError as exc:
            logger.warning("groq_timeout")
            raise LLMTimeoutError() from exc
        except RateLimitError as exc:
            logger.warning("groq_rate_limited", retry_after=getattr(exc, "retry_after", None))
            raise LLMRateLimitError() from exc
        except APIConnectionError as exc:
            logger.warning("groq_connection_error", error=str(exc))
            raise LLMProviderUnavailableError() from exc
        except APIStatusError as exc:
            logger.warning("groq_status_error", status_code=exc.status_code, error=str(exc))
            if exc.status_code == 429:
                raise LLMRateLimitError() from exc
            raise LLMProviderUnavailableError() from exc
        except APIError as exc:
            logger.error("groq_api_error", error=str(exc))
            raise LLMProviderUnavailableError() from exc

        if not response.choices:
            raise LLMProviderUnavailableError("LLM returned no choices")

        content = response.choices[0].message.content
        if not content:
            raise LLMProviderUnavailableError("LLM returned empty content")

        return str(content)
