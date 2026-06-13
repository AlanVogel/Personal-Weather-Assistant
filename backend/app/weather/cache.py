"""Async-safe in-memory TTL cache for weather data."""

import asyncio
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass(slots=True)
class _CacheEntry[T]:
    value: T
    expires_at: float


class WeatherCache:
    """In-memory TTL cache with single-flight semantics for cache misses.

    A single-process cache suited to demo / small deployments; for multi-instance
    production, swap it for Redis behind the same interface. A per-key
    ``asyncio.Lock`` prevents a thundering herd on misses: when several requests
    miss the same key at once, only one runs the factory and the rest await it.
    """

    def __init__(self, ttl_seconds: int) -> None:
        self._ttl = ttl_seconds
        self._store: dict[str, _CacheEntry[object]] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self._locks_lock = asyncio.Lock()

    async def get_or_set(self, key: str, factory: Callable[[], Awaitable[object]]) -> object:
        """Return the cached value, or compute and store it on miss/expiry.

        Args:
            key: Cache key (e.g. a normalized city name).
            factory: Async callable producing the value on a miss.

        Returns:
            The cached or freshly computed value. Guaranteed to invoke
            ``factory`` at most once per key even under concurrent access.
        """
        # Fast path: cache hit
        if entry := self._get_valid_entry(key):
            return entry.value

        # Slow path: serialize concurrent misses on the same key
        lock = await self._get_lock(key)
        try:
            async with lock:
                # Re-check after acquiring lock — another waiter may have populated
                if entry := self._get_valid_entry(key):
                    return entry.value

                value = await factory()
                self._store[key] = _CacheEntry(value=value, expires_at=time.monotonic() + self._ttl)
                return value
        finally:
            await self._prune_lock(key, lock)

    def get(self, key: str) -> object | None:
        """Return cached value if present and not expired, else None."""
        if entry := self._get_valid_entry(key):
            return entry.value
        return None

    def invalidate(self, key: str) -> None:
        """Remove a single key from the cache."""
        self._store.pop(key, None)

    def clear(self) -> None:
        """Remove all entries. Useful in tests."""
        self._store.clear()
        self._locks.clear()

    def _get_valid_entry(self, key: str) -> _CacheEntry[object] | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        if entry.expires_at <= time.monotonic():
            del self._store[key]
            return None
        return entry

    async def _get_lock(self, key: str) -> asyncio.Lock:
        async with self._locks_lock:
            if key not in self._locks:
                self._locks[key] = asyncio.Lock()
            return self._locks[key]

    async def _prune_lock(self, key: str, lock: asyncio.Lock) -> None:
        """Drop the per-key lock once it's free, keeping the lock map bounded.

        Without this, the lock dict would grow by one entry per distinct key
        forever. A rare race (a new waiter arriving between release and prune)
        costs at most one redundant factory call — never correctness.
        """
        async with self._locks_lock:
            if self._locks.get(key) is lock and not lock.locked():
                del self._locks[key]
