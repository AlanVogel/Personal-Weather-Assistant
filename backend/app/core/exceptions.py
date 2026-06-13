"""Domain-specific exception hierarchy and HTTP handlers."""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.core.logging import get_logger

logger = get_logger(__name__)


class AppError(Exception):
    """Base for all application errors, each carrying its HTTP mapping.

    Subclasses set ``status_code`` and ``default_message``; a single registered
    handler translates any ``AppError`` into a JSON response. This keeps the HTTP
    concern out of services, which just raise meaningful domain exceptions.
    """

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_message: str = "An unexpected error occurred"

    def __init__(self, message: str | None = None, **context: object) -> None:
        super().__init__(message or self.default_message)
        self.message = message or self.default_message
        self.context = context


# Weather domain errors
class WeatherError(AppError):
    """Base for weather-related errors."""


class CityNotFoundError(WeatherError):
    """Provided city name could not be resolved."""

    status_code = status.HTTP_404_NOT_FOUND
    default_message = "City not found"


class WeatherProviderUnavailableError(WeatherError):
    """Upstream weather provider is unavailable or returned an error."""

    status_code = status.HTTP_502_BAD_GATEWAY
    default_message = "Weather service temporarily unavailable"


class WeatherProviderTimeoutError(WeatherError):
    """Weather provider did not respond in time."""

    status_code = status.HTTP_504_GATEWAY_TIMEOUT
    default_message = "Weather service timeout"


# LLM domain errors
class LLMError(AppError):
    """Base for LLM-related errors."""


class LLMParseError(LLMError):
    """LLM returned content that could not be parsed."""

    status_code = status.HTTP_502_BAD_GATEWAY
    default_message = "AI service returned invalid response"


class LLMRateLimitError(LLMError):
    """LLM provider rate-limited us."""

    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_message = "AI service rate limit exceeded"


class LLMTimeoutError(LLMError):
    """LLM provider did not respond in time."""

    status_code = status.HTTP_504_GATEWAY_TIMEOUT
    default_message = "AI service timeout"


class LLMProviderUnavailableError(LLMError):
    """LLM provider is unavailable."""

    status_code = status.HTTP_502_BAD_GATEWAY
    default_message = "AI service temporarily unavailable"


# Validation errors
class InvalidDateRangeError(AppError):
    """Requested date is outside supported forecast range."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_message = "Date must be within the forecast range (today + 5 days)"


def register_exception_handlers(app: FastAPI) -> None:
    """Register exception handlers that translate AppError to HTTP responses.

    Single global handler keeps routers clean — they raise typed exceptions,
    framework handles HTTP translation and logging.
    """

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        logger.warning(
            "application_error",
            error_type=type(exc).__name__,
            message=exc.message,
            status_code=exc.status_code,
            path=request.url.path,
            **exc.context,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": type(exc).__name__,
                "detail": exc.message,
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(
            "unhandled_exception",
            error_type=type(exc).__name__,
            path=request.url.path,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "InternalServerError",
                "detail": "An unexpected error occurred",
            },
        )
