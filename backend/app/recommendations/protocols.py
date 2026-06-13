"""Protocol for AI recommendation generators."""

from typing import Protocol, runtime_checkable

from app.recommendations.models import DailyRecommendation, FollowUpAnswer
from app.weather.models import WeatherSnapshot


@runtime_checkable
class IRecommendationGenerator(Protocol):
    """Contract for any AI service that generates weather-based recommendations.

    Consumers depend on this Protocol rather than the Groq client, so the LLM
    backend can be swapped (or faked in tests) without changing consumer code.
    """

    async def generate(
        self,
        weather: WeatherSnapshot,
        target_date_iso: str,
    ) -> DailyRecommendation:
        """Generate personalized recommendations from weather data.

        Args:
            weather: Current conditions and forecast for the city.
            target_date_iso: ISO-8601 date the advice should target.

        Returns:
            A validated ``DailyRecommendation``.

        Raises:
            LLMTimeoutError: Provider did not respond in time.
            LLMRateLimitError: Rate limit exceeded.
            LLMParseError: Response could not be parsed into the expected schema.
            LLMProviderUnavailableError: Provider unavailable.
        """
        ...

    async def follow_up(
        self,
        weather: WeatherSnapshot,
        previous_recommendation: DailyRecommendation,
        user_question: str,
    ) -> FollowUpAnswer:
        """Answer a follow-up question using the previous recommendation as context.

        Args:
            weather: Current conditions for the city.
            previous_recommendation: The recommendation being asked about.
            user_question: The user's free-text follow-up question.

        Returns:
            A ``FollowUpAnswer`` with a short conversational reply.
        """
        ...
