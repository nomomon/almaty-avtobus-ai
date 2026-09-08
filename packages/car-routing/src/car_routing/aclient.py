"""Asynchronous client for the 2GIS car routing endpoint.

Same surface as :class:`car_routing.CarRoutingClient`, awaitable, for use
inside an event loop (FastAPI and friends) where the sync client would block.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterable
from typing import Any

import httpx

from ._core import (
    BROWSER_HEADERS,
    DEFAULT_BASE_URL,
    RETRY_STATUSES,
    TRAFFIC_ROUTE_TYPE,
    CarRoutingError,
    backoff_seconds,
    build_body,
    check_status,
    parse_routes,
    resolve_key,
    same_place,
)
from .models import DistanceMatrix, MatrixCell, Point, Route

__all__ = ["AsyncCarRoutingClient"]


class AsyncCarRoutingClient:
    """Travel time and distance by car, awaitable.

    ::

        async with AsyncCarRoutingClient() as client:
            route = await client.route(a, b)
            matrix = await client.matrix(points)

    Concurrency is bounded by ``max_concurrency`` regardless of how many pairs
    a matrix asks for, so a big matrix cannot open hundreds of sockets at once.
    """

    def __init__(
        self,
        key: str | None = None,
        *,
        locale: str = "ru",
        route_type: str = TRAFFIC_ROUTE_TYPE,
        allow_locked_roads: bool = True,
        timeout: float = 20.0,
        max_concurrency: int = 8,
        max_retries: int = 3,
        base_url: str = DEFAULT_BASE_URL,
        headers: dict[str, str] | None = None,
        extra_body: dict[str, Any] | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.key = resolve_key(key)
        self.locale = locale
        self.route_type = route_type
        self.allow_locked_roads = allow_locked_roads
        self.max_concurrency = max(1, max_concurrency)
        self.max_retries = max(0, max_retries)
        self.base_url = base_url
        self.extra_body = dict(extra_body or {})

        self._headers = {**BROWSER_HEADERS, **(headers or {})}
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            timeout=timeout,
            headers=self._headers,
            limits=httpx.Limits(max_connections=self.max_concurrency * 2),
        )
        # Created lazily: a semaphore must be bound to the running loop, and
        # __init__ may run before there is one.
        self._semaphore: asyncio.Semaphore | None = None

    # -- lifecycle ---------------------------------------------------------

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> AsyncCarRoutingClient:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.aclose()

    def _gate(self) -> asyncio.Semaphore:
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self.max_concurrency)
        return self._semaphore

    # -- single routes -----------------------------------------------------

    async def alternatives(self, origin: Any, destination: Any) -> list[Route]:
        """Every route the server offers, fastest first."""
        a, b = Point.coerce(origin), Point.coerce(destination)
        payload = await self._post(
            build_body(
                a,
                b,
                locale=self.locale,
                route_type=self.route_type,
                allow_locked_roads=self.allow_locked_roads,
                extra=self.extra_body,
            )
        )
        return parse_routes(payload, a, b)

    async def route(self, origin: Any, destination: Any) -> Route:
        """The fastest route."""
        return (await self.alternatives(origin, destination))[0]

    # -- matrix ------------------------------------------------------------

    async def matrix(
        self,
        origins: Iterable[Any],
        destinations: Iterable[Any] | None = None,
    ) -> DistanceMatrix:
        """Time and distance for every origin-destination pair.

        One request per pair, ``max_concurrency`` in flight. A pair that fails
        records its error on its own cell instead of sinking the matrix.
        """
        from_points = Point.coerce_all(origins)
        to_points = (
            from_points if destinations is None else Point.coerce_all(destinations)
        )

        if not from_points or not to_points:
            raise CarRoutingError("matrix() needs at least one origin and destination")

        cells: dict[tuple[int, int], MatrixCell] = {
            (i, j): MatrixCell(origin=i, destination=j, distance_m=0, duration_s=0)
            for i in range(len(from_points))
            for j in range(len(to_points))
        }
        pairs = [
            (i, j)
            for i in range(len(from_points))
            for j in range(len(to_points))
            if not same_place(from_points[i], to_points[j])
        ]

        if pairs:
            fetched = await asyncio.gather(
                *(self._one_cell(from_points[i], to_points[j], i, j) for i, j in pairs)
            )
            for cell in fetched:
                cells[(cell.origin, cell.destination)] = cell

        return DistanceMatrix(
            origins=from_points,
            destinations=to_points,
            cells=[
                [cells[(i, j)] for j in range(len(to_points))]
                for i in range(len(from_points))
            ],
        )

    async def _one_cell(self, a: Point, b: Point, i: int, j: int) -> MatrixCell:
        try:
            best = await self.route(a, b)
        except CarRoutingError as exc:
            return MatrixCell(origin=i, destination=j, error=str(exc))
        return MatrixCell(
            origin=i,
            destination=j,
            distance_m=best.distance_m,
            duration_s=best.duration_s,
        )

    # -- transport ---------------------------------------------------------

    async def _post(self, body: dict[str, Any]) -> Any:
        last_error: Exception | None = None

        async with self._gate():
            for attempt in range(self.max_retries + 1):
                if attempt:
                    await asyncio.sleep(backoff_seconds(attempt))
                try:
                    response = await self._client.post(
                        self.base_url, params={"key": self.key}, json=body
                    )
                except httpx.HTTPError as exc:
                    last_error = CarRoutingError(f"request failed: {exc}")
                    continue

                if response.status_code in RETRY_STATUSES:
                    last_error = CarRoutingError(
                        f"HTTP {response.status_code} from 2GIS",
                        status=response.status_code,
                        body=response.text[:300],
                    )
                    continue

                failure = check_status(response.status_code, response.text)
                if failure is not None:
                    raise failure

                try:
                    return response.json()
                except ValueError as exc:
                    raise CarRoutingError(
                        f"2GIS returned invalid JSON: {exc}",
                        status=response.status_code,
                        body=response.text[:300],
                    ) from exc

        raise last_error or CarRoutingError("request failed for an unknown reason")
