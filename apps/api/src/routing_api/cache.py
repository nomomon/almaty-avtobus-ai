"""Pair-level Redis cache.

Caching happens per origin-destination *pair*, not per request, which is what
makes it worth having: a matrix request reuses pairs cached by earlier route
calls and by overlapping matrices, so repeatedly asking about the same stops
costs nothing upstream.

The cache is best-effort by design. If Redis is down, unreachable, or slow,
every operation degrades to a miss and the service keeps answering from
upstream -- a cache outage must not become an API outage.
"""

from __future__ import annotations

import json
import logging
from typing import Protocol

from car_routing import Point, Route

logger = logging.getLogger(__name__)


class CacheBackend(Protocol):
    """The slice of redis.asyncio.Redis this module needs.

    Narrow on purpose, so tests can pass a dict-backed fake.
    """

    async def get(self, key: str) -> bytes | str | None: ...

    async def set(self, key: str, value: str, ex: int | None = None) -> object: ...


class RouteCache:
    """Stores ``(distance_m, duration_s)`` per pair, with a TTL."""

    def __init__(
        self,
        backend: CacheBackend | None,
        *,
        ttl_s: int = 600,
        prefix: str = "route:v1",
        coord_precision: int = 5,
        route_type: str = "online5",
    ) -> None:
        self.backend = backend
        self.ttl_s = ttl_s
        self.prefix = prefix
        self.coord_precision = coord_precision
        self.route_type = route_type
        self._warned = False

    @property
    def enabled(self) -> bool:
        return self.backend is not None and self.ttl_s > 0

    def key_for(self, a: Point, b: Point) -> str:
        p = self.coord_precision
        return (
            f"{self.prefix}:{self.route_type}:"
            f"{round(a.lon, p)},{round(a.lat, p)}:"
            f"{round(b.lon, p)},{round(b.lat, p)}"
        )

    async def get(self, a: Point, b: Point) -> Route | None:
        if not self.enabled:
            return None
        try:
            raw = await self.backend.get(self.key_for(a, b))  # type: ignore[union-attr]
        except Exception as exc:  # redis down, timeout, auth, anything
            self._warn_once("read", exc)
            return None

        if raw is None:
            return None

        try:
            payload = json.loads(raw)
            return Route.model_validate(payload)
        except (ValueError, TypeError) as exc:
            # Poisoned or stale-format entry: treat as a miss rather than
            # failing the request. It will be overwritten by the refetch.
            logger.warning("discarding unreadable cache entry: %s", exc)
            return None

    async def set(self, a: Point, b: Point, route: Route) -> None:
        if not self.enabled:
            return
        try:
            await self.backend.set(  # type: ignore[union-attr]
                self.key_for(a, b),
                route.model_dump_json(),
                ex=self.ttl_s,
            )
        except Exception as exc:
            self._warn_once("write", exc)

    def _warn_once(self, operation: str, exc: Exception) -> None:
        if not self._warned:
            self._warned = True
            logger.warning(
                "cache %s failed (%s: %s); serving uncached from here on",
                operation,
                type(exc).__name__,
                exc,
            )


async def make_backend(redis_url: str) -> CacheBackend | None:
    """Connect to Redis, or return None if it is not usable.

    Never raises: a missing cache is a degraded mode, not a startup failure.
    """
    try:
        from redis.asyncio import Redis

        backend = Redis.from_url(redis_url, decode_responses=True)
        await backend.ping()
    except Exception as exc:
        logger.warning(
            "no cache: cannot reach Redis at %s (%s: %s)",
            redis_url,
            type(exc).__name__,
            exc,
        )
        return None

    logger.info("cache ready at %s", redis_url)
    return backend
