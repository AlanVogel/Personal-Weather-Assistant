"""Dependency injection setup."""

import asyncio
from dataclasses import dataclass
from typing import cast

import httpx
from fastapi import Depends, Request
from groq import AsyncGroq

from app.core.config import Settings, get_settings
from app.recommendations.protocols import IRecommendationGenerator
from app.recommendations.service import RecommendationService
from app.weather.cache import WeatherCache
from app.weather.openweather_client import OpenWeatherMapClient
from app.weather.protocols import IWeatherProvider
from app.weather.service import WeatherService


@dataclass(slots=True)
class LifespanClients:
    """Long-lived clients held on ``app.state`` for the application's lifetime.

    The httpx and Groq clients are created once at startup and reused across all
    requests (per-request services wrap but don't own them), which avoids socket
    leaks and connection-pool churn. Semaphores bound concurrency to the
    external providers.
    """

    http_client: httpx.AsyncClient
    groq_client: AsyncGroq
    weather_cache: WeatherCache
    llm_semaphore: asyncio.Semaphore
    weather_semaphore: asyncio.Semaphore


async def get_lifespan_clients(settings: Settings) -> LifespanClients:
    """Create clients once at application startup."""
    http_client = httpx.AsyncClient(
        timeout=httpx.Timeout(settings.weather_timeout_seconds),
        limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
    )
    groq_client = AsyncGroq(api_key=settings.groq_api_key, timeout=settings.llm_timeout_seconds)
    weather_cache = WeatherCache(ttl_seconds=settings.cache_ttl_seconds)

    return LifespanClients(
        http_client=http_client,
        groq_client=groq_client,
        weather_cache=weather_cache,
        llm_semaphore=asyncio.Semaphore(settings.max_concurrent_llm_calls),
        weather_semaphore=asyncio.Semaphore(settings.max_concurrent_weather_calls),
    )


async def shutdown_lifespan_clients(clients: LifespanClients) -> None:
    """Clean up clients at application shutdown."""
    await clients.http_client.aclose()
    # Groq client uses httpx under the hood; closing happens automatically


def get_clients(request: Request) -> LifespanClients:
    """Retrieve the lifespan clients stored on app.state."""
    return cast(LifespanClients, request.app.state.clients)


def get_weather_provider(
    clients: LifespanClients = Depends(get_clients),
    settings: Settings = Depends(get_settings),
) -> IWeatherProvider:
    """Provide an IWeatherProvider implementation per request.

    Returns the Protocol, not the concrete class. This lets us swap providers
    (or use FakeWeatherProvider in tests) without changing consumer code.
    """
    return OpenWeatherMapClient(
        http_client=clients.http_client,
        api_key=settings.openweather_api_key,
        units=settings.weather_units,
        semaphore=clients.weather_semaphore,
    )


def get_weather_service(
    provider: IWeatherProvider = Depends(get_weather_provider),
    clients: LifespanClients = Depends(get_clients),
) -> WeatherService:
    """Provide a WeatherService that handles caching + business rules."""
    return WeatherService(provider=provider, cache=clients.weather_cache)


def get_recommendation_generator(
    clients: LifespanClients = Depends(get_clients),
    settings: Settings = Depends(get_settings),
) -> IRecommendationGenerator:
    """Provide an IRecommendationGenerator implementation per request."""
    from app.recommendations.groq_generator import GroqRecommendationGenerator

    return GroqRecommendationGenerator(
        client=clients.groq_client,
        model=settings.groq_model,
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
        semaphore=clients.llm_semaphore,
    )


def get_recommendation_service(
    weather_service: WeatherService = Depends(get_weather_service),
    generator: IRecommendationGenerator = Depends(get_recommendation_generator),
) -> RecommendationService:
    """Provide the orchestrating service that combines weather + AI."""
    return RecommendationService(weather_service=weather_service, generator=generator)
