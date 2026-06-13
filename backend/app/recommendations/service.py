"""Recommendation service: orchestrates weather fetch + AI generation."""

from datetime import date, timedelta

from app.core.exceptions import InvalidDateRangeError
from app.core.logging import get_logger
from app.recommendations.models import (
    DailyRecommendation,
    FollowUpAnswer,
    WeatherWithRecommendation,
)
from app.recommendations.protocols import IRecommendationGenerator
from app.weather.service import WeatherService

logger = get_logger(__name__)

_FORECAST_DAYS_LIMIT = 5


class RecommendationService:
    """Orchestrates weather fetching and AI recommendation generation.

    This is the primary use-case service. It combines two collaborators
    (weather data, AI generation) into a single business operation.
    """

    def __init__(
        self,
        weather_service: WeatherService,
        generator: IRecommendationGenerator,
    ) -> None:
        self._weather = weather_service
        self._generator = generator

    async def get_recommendation(
        self,
        city: str,
        target_date: date | None = None,
    ) -> WeatherWithRecommendation:
        """Fetch weather and generate an AI recommendation for a date.

        Args:
            city: City name, optionally with a country code.
            target_date: Day to advise for. Defaults to today; must fall within
                today + 5 days (the free-tier forecast horizon).

        Returns:
            A ``WeatherWithRecommendation`` combining the weather snapshot and
            the generated recommendation.

        Raises:
            InvalidDateRangeError: ``target_date`` is in the past or beyond the
                forecast horizon.
            (Weather and LLM provider errors propagate from the collaborators.)
        """
        target = target_date or date.today()
        self._validate_date(target)

        logger.info(
            "recommendation_requested",
            city=city,
            target_date=target.isoformat(),
        )

        # Always fetch the forecast: it's a single extra call (run concurrently
        # with the current-weather call) that powers both future-date targeting
        # and the multi-day "weekly advice".
        weather = await self._weather.get_weather(city, include_forecast=True)
        recommendation = await self._generator.generate(weather, target.isoformat())

        return WeatherWithRecommendation(
            target_date=target,
            weather=weather,
            recommendation=recommendation,
        )

    async def ask_followup(
        self,
        city: str,
        target_date: date,
        previous_recommendation: DailyRecommendation,
        user_question: str,
    ) -> FollowUpAnswer:
        """Answer a follow-up question using the prior recommendation as context.

        Args:
            city: City name, optionally with a country code.
            target_date: The date the original recommendation targeted.
            previous_recommendation: The recommendation the user is asking about.
            user_question: The user's free-text follow-up question.

        Returns:
            A ``FollowUpAnswer`` with a short conversational reply.

        Raises:
            InvalidDateRangeError: ``target_date`` is outside the supported range.
        """
        self._validate_date(target_date)

        logger.info(
            "followup_requested",
            city=city,
            target_date=target_date.isoformat(),
            question_length=len(user_question),
        )

        weather = await self._weather.get_weather(city, include_forecast=False)
        return await self._generator.follow_up(weather, previous_recommendation, user_question)

    @staticmethod
    def _validate_date(target: date) -> None:
        today = date.today()
        max_date = today + timedelta(days=_FORECAST_DAYS_LIMIT)
        if target < today:
            raise InvalidDateRangeError("Cannot provide recommendations for past dates")
        if target > max_date:
            raise InvalidDateRangeError(
                f"Date must be within {_FORECAST_DAYS_LIMIT} days from today"
            )
