"""A two-line cache interface with a Redis implementation and an in-process fallback.

The fallback matters: it means the service, the tests, and a laptop with no Redis
running all take the same code path instead of sprouting `if cache is None` checks.
"""

import time
from typing import Protocol, cast

import redis.asyncio as aioredis

from app.config import Settings


class Cache(Protocol):
    async def get(self, key: str) -> str | None: ...
    async def set(self, key: str, value: str, ttl: int) -> None: ...
    async def delete(self, key: str) -> None: ...
    async def ping(self) -> bool: ...
    async def close(self) -> None: ...


class InMemoryCache:
    """Per-process, TTL-aware. Correct for one worker; useless across replicas."""

    def __init__(self) -> None:
        self._data: dict[str, tuple[float, str]] = {}

    async def get(self, key: str) -> str | None:
        entry = self._data.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if expires_at < time.monotonic():
            self._data.pop(key, None)
            return None
        return value

    async def set(self, key: str, value: str, ttl: int) -> None:
        self._data[key] = (time.monotonic() + ttl, value)

    async def delete(self, key: str) -> None:
        self._data.pop(key, None)

    async def ping(self) -> bool:
        return True

    async def close(self) -> None:
        self._data.clear()


class RedisCache:
    def __init__(self, url: str) -> None:
        self._client = aioredis.from_url(url, decode_responses=True)

    async def get(self, key: str) -> str | None:
        # decode_responses=True means str, but the stubs still say bytes | str.
        return cast("str | None", await self._client.get(key))

    async def set(self, key: str, value: str, ttl: int) -> None:
        await self._client.set(key, value, ex=ttl)

    async def delete(self, key: str) -> None:
        await self._client.delete(key)

    async def ping(self) -> bool:
        try:
            return bool(await self._client.ping())
        except Exception:
            return False

    async def close(self) -> None:
        await self._client.aclose()


def build_cache(settings: Settings) -> Cache:
    return RedisCache(settings.redis_url) if settings.redis_url else InMemoryCache()
