"""Routing with the cache in front of it.

Keeps the cache-aside logic in one place so the HTTP layer stays thin, and so
the pair-level accounting (hit / fetched / trivial / failed) is computed once.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field

from car_routing import AsyncCarRoutingClient, CarRoutingError, Point, Route

from .cache import RouteCache


@dataclass
class MatrixOutcome:
    durations_s: list[list[int | None]]
    distances_m: list[list[int | None]]
    failures: list[tuple[int, int, str]] = field(default_factory=list)
    from_cache: int = 0
    fetched: int = 0
    trivial: int = 0
    elapsed_ms: int = 0

    @property
    def pairs(self) -> int:
        return sum(len(row) for row in self.durations_s)


class RoutingService:
    def __init__(self, client: AsyncCarRoutingClient, cache: RouteCache) -> None:
        self.client = client
        self.cache = cache

    async def route(self, origin: Point, destination: Point) -> tuple[Route, bool]:
        """Return the fastest route and whether it came from the cache."""
        # Going nowhere takes no time. Answering this upstream wastes a call
        # and, on a key-less deploy, turns a no-op into a confusing 502.
        if _same_place(origin, destination):
            return Route(distance_m=0, duration_s=0), False

        hit = await self.cache.get(origin, destination)
        if hit is not None:
            return hit, True

        route = await self.client.route(origin, destination)
        await self.cache.set(origin, destination, route)
        return route, False

    async def matrix(
        self, origins: list[Point], destinations: list[Point] | None = None
    ) -> MatrixOutcome:
        started = time.perf_counter()
        targets = origins if destinations is None else destinations

        rows_duration: list[list[int | None]] = []
        rows_distance: list[list[int | None]] = []
        failures: list[tuple[int, int, str]] = []
        counts = {"cache": 0, "fetched": 0, "trivial": 0}

        async def one(i: int, j: int) -> tuple[int, int, Route | None, str | None, str]:
            a, b = origins[i], targets[j]
            if _same_place(a, b):
                return i, j, Route(distance_m=0, duration_s=0), None, "trivial"
            try:
                route, cached = await self.route(a, b)
            except CarRoutingError as exc:
                return i, j, None, str(exc), "failed"
            return i, j, route, None, "cache" if cached else "fetched"

        results = await asyncio.gather(
            *(one(i, j) for i in range(len(origins)) for j in range(len(targets)))
        )

        by_cell = {
            (i, j): (route, error, source) for i, j, route, error, source in results
        }
        for i in range(len(origins)):
            duration_row: list[int | None] = []
            distance_row: list[int | None] = []
            for j in range(len(targets)):
                route, error, source = by_cell[(i, j)]
                if source in counts:
                    counts[source] += 1
                if route is None:
                    duration_row.append(None)
                    distance_row.append(None)
                    failures.append((i, j, error or "unknown error"))
                else:
                    duration_row.append(route.duration_s)
                    distance_row.append(route.distance_m)
            rows_duration.append(duration_row)
            rows_distance.append(distance_row)

        return MatrixOutcome(
            durations_s=rows_duration,
            distances_m=rows_distance,
            failures=failures,
            from_cache=counts["cache"],
            fetched=counts["fetched"],
            trivial=counts["trivial"],
            elapsed_ms=int((time.perf_counter() - started) * 1000),
        )


def _same_place(a: Point, b: Point, tolerance: float = 1e-6) -> bool:
    return abs(a.lon - b.lon) < tolerance and abs(a.lat - b.lat) < tolerance
