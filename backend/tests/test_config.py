"""Tests for settings parsing — especially ALLOWED_ORIGINS from env vars.

pydantic-settings v2 JSON-decodes list-typed fields before validators run, so a
plain or comma-separated ALLOWED_ORIGINS value would crash startup without the
`NoDecode` annotation. These tests lock that behavior (it broke the Railway
deploy once).
"""

import pytest

from app.core.config import Settings


@pytest.fixture(autouse=True)
def _required_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENWEATHER_API_KEY", "x" * 12)
    monkeypatch.setenv("GROQ_API_KEY", "x" * 12)


def test_allowed_origins_single_plain_string(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://my-app.vercel.app")
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.allowed_origins == ["https://my-app.vercel.app"]


def test_allowed_origins_comma_separated(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://a.vercel.app, https://b.vercel.app")
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.allowed_origins == ["https://a.vercel.app", "https://b.vercel.app"]


def test_allowed_origins_defaults_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.allowed_origins == [
        "http://localhost:5173",
        "http://localhost:3000",
    ]
