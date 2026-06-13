"""Recommendation API endpoints."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.core.config import get_settings
from app.core.dependencies import get_recommendation_service
from app.core.rate_limit import limiter
from app.recommendations.models import (
    DailyRecommendation,
    FollowUpAnswer,
    WeatherWithRecommendation,
)
from app.recommendations.service import RecommendationService

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])

_RATE_LIMIT = get_settings().rate_limit


class RecommendationRequest(BaseModel):
    """Request body for initial recommendation."""

    model_config = ConfigDict(extra="forbid")

    city: Annotated[str, StringConstraints(min_length=1, max_length=100, strip_whitespace=True)] = (
        Field(description="City name, optionally with country code (e.g., 'Zagreb' or 'London,UK')")
    )
    target_date: date | None = Field(
        default=None,
        description="Target date for recommendation. Defaults to today.",
    )


class FollowUpRequest(BaseModel):
    """Request body for follow-up question."""

    model_config = ConfigDict(extra="forbid")

    city: Annotated[str, StringConstraints(min_length=1, max_length=100, strip_whitespace=True)]
    target_date: date
    previous_recommendation: DailyRecommendation
    user_question: Annotated[
        str, StringConstraints(min_length=3, max_length=500, strip_whitespace=True)
    ]


@router.post("", response_model=WeatherWithRecommendation)
@limiter.limit(_RATE_LIMIT)
async def get_recommendation(
    request: Request,
    body: RecommendationRequest,
    service: RecommendationService = Depends(get_recommendation_service),
) -> WeatherWithRecommendation:
    """Get weather data with AI-powered personalized recommendations.

    Returns current weather, 5-day forecast, and structured recommendations
    for clothing, activities, and health tips. Rate-limited per client IP
    (``request`` is required by the limiter to identify the caller).
    """
    return await service.get_recommendation(
        city=body.city,
        target_date=body.target_date,
    )


@router.post("/followup", response_model=FollowUpAnswer)
@limiter.limit(_RATE_LIMIT)
async def ask_followup(
    request: Request,
    body: FollowUpRequest,
    service: RecommendationService = Depends(get_recommendation_service),
) -> FollowUpAnswer:
    """Ask a follow-up question with context from a previous recommendation.

    Rate-limited per client IP (``request`` is required by the limiter).
    """
    return await service.ask_followup(
        city=body.city,
        target_date=body.target_date,
        previous_recommendation=body.previous_recommendation,
        user_question=body.user_question,
    )
