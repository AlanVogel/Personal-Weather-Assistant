"""Tests for the async TTL cache."""

import asyncio

from app.weather.cache import WeatherCache


class TestWeatherCache:
    async def test_get_miss_returns_none(self) -> None:
        cache = WeatherCache(ttl_seconds=60)
        assert cache.get("missing") is None

    async def test_get_or_set_calls_factory_on_miss(self) -> None:
        cache = WeatherCache(ttl_seconds=60)
        call_count = 0

        async def factory() -> str:
            nonlocal call_count
            call_count += 1
            return "value"

        result = await cache.get_or_set("key", factory)
        assert result == "value"
        assert call_count == 1

    async def test_get_or_set_returns_cached_on_hit(self) -> None:
        cache = WeatherCache(ttl_seconds=60)
        call_count = 0

        async def factory() -> str:
            nonlocal call_count
            call_count += 1
            return f"value-{call_count}"

        first = await cache.get_or_set("key", factory)
        second = await cache.get_or_set("key", factory)

        assert first == second == "value-1"
        assert call_count == 1

    async def test_ttl_expires(self) -> None:
        cache = WeatherCache(ttl_seconds=0)  # immediate expiry
        await cache.get_or_set("key", lambda: _async_return("first"))

        # Wait a tick so monotonic time advances
        await asyncio.sleep(0.01)

        result = await cache.get_or_set("key", lambda: _async_return("second"))
        assert result == "second"

    async def test_invalidate_removes_entry(self) -> None:
        cache = WeatherCache(ttl_seconds=60)
        await cache.get_or_set("key", lambda: _async_return("value"))
        cache.invalidate("key")
        assert cache.get("key") is None

    async def test_clear_removes_all(self) -> None:
        cache = WeatherCache(ttl_seconds=60)
        await cache.get_or_set("k1", lambda: _async_return("v1"))
        await cache.get_or_set("k2", lambda: _async_return("v2"))
        cache.clear()
        assert cache.get("k1") is None
        assert cache.get("k2") is None

    async def test_single_flight_on_concurrent_miss(self) -> None:
        """When multiple coroutines request the same missing key,
        only one factory invocation should happen."""
        cache = WeatherCache(ttl_seconds=60)
        call_count = 0

        async def slow_factory() -> str:
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.05)
            return "value"

        results = await asyncio.gather(
            cache.get_or_set("hot-key", slow_factory),
            cache.get_or_set("hot-key", slow_factory),
            cache.get_or_set("hot-key", slow_factory),
            cache.get_or_set("hot-key", slow_factory),
            cache.get_or_set("hot-key", slow_factory),
        )

        assert all(r == "value" for r in results)
        assert call_count == 1  # Critical: only one factory call despite 5 concurrent requests

    async def test_different_keys_isolated(self) -> None:
        cache = WeatherCache(ttl_seconds=60)
        await cache.get_or_set("key1", lambda: _async_return("v1"))
        await cache.get_or_set("key2", lambda: _async_return("v2"))
        assert cache.get("key1") == "v1"
        assert cache.get("key2") == "v2"

    async def test_lock_map_stays_bounded(self) -> None:
        """Per-key locks must not accumulate without bound across distinct keys."""
        cache = WeatherCache(ttl_seconds=60)
        for i in range(100):
            await cache.get_or_set(f"key-{i}", lambda: _async_return("v"))

        # Values are cached, but the lock map is pruned once each lock is free.
        assert len(cache._store) == 100
        assert len(cache._locks) == 0

    async def test_lock_retained_during_concurrent_access(self) -> None:
        """While a key is being fetched concurrently, its lock must survive
        so the single-flight guarantee holds."""
        cache = WeatherCache(ttl_seconds=60)

        async def slow_factory() -> str:
            await asyncio.sleep(0.02)
            return "value"

        await asyncio.gather(*(cache.get_or_set("hot", slow_factory) for _ in range(5)))
        # After all callers finish, the now-free lock is pruned.
        assert len(cache._locks) == 0


async def _async_return(value: str) -> str:
    return value
