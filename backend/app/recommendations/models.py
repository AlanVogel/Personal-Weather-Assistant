"""Recommendation domain models — schemas for validated LLM output."""

from datetime import date
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.weather.models import WeatherSnapshot


class Priority(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ClothingAdvice(BaseModel):
    """Specific clothing recommendations."""

    model_config = ConfigDict(frozen=True)

    items: Annotated[list[str], Field(min_length=1, max_length=10)] = Field(
        description="Specific clothing items to wear today"
    )
    reasoning: Annotated[str, Field(min_length=10, max_length=300)] = Field(
        description="One-sentence explanation"
    )


class ActivityAdvice(BaseModel):
    """Activity suggestions for the day."""

    model_config = ConfigDict(frozen=True)

    suggested: Annotated[list[str], Field(min_length=1, max_length=8)]
    avoid: Annotated[list[str], Field(max_length=5)] = Field(default_factory=list)
    reasoning: Annotated[str, Field(min_length=10, max_length=300)]


class HealthTip(BaseModel):
    """A single health-related tip."""

    model_config = ConfigDict(frozen=True)

    tip: Annotated[str, Field(min_length=5, max_length=200)]
    priority: Priority = Priority.MEDIUM


class DailyRecommendation(BaseModel):
    """Complete recommendations for a single day's weather."""

    model_config = ConfigDict(frozen=True)

    summary: Annotated[str, Field(min_length=10, max_length=200)] = Field(
        description="One-sentence summary of the day's weather and outlook"
    )
    clothing: ClothingAdvice
    activities: ActivityAdvice
    health_tips: Annotated[list[HealthTip], Field(max_length=5)] = Field(default_factory=list)
    weekly_advice: str | None = Field(
        default=None,
        description="Optional multi-day planning advice, if forecast was provided",
        max_length=500,
    )


class FollowUpAnswer(BaseModel):
    """Conversational follow-up response."""

    model_config = ConfigDict(frozen=True)

    answer: Annotated[str, Field(min_length=10, max_length=1000)]


class WeatherWithRecommendation(BaseModel):
    """Combined weather data + AI recommendations.

    This is the primary response shape consumed by the frontend.
    """

    model_config = ConfigDict(frozen=True)

    target_date: date
    weather: WeatherSnapshot
    recommendation: DailyRecommendation
