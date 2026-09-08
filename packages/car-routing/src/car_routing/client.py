"""Synchronous client for the 2GIS car routing endpoint."""

from __future__ import annotations

import time
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import httpx

from ._core import (
    BROWSER_HEADERS,
    DEFAULT_BASE_URL,
    KEY_ENV_VARS,
    RETRY_STATUSES,
    TRAFFIC_ROUTE_TYPE,
    CarRoutingError,
    DeadKeyError,
    backoff_seconds,
    build_body,
    check_status,
    parse_routes,
    resolve_key,
    same_place,
)
from .models import DistanceMatrix, MatrixCell, Point, Route

__all__ = [
    "CarRoutingClient",
    "CarRoutingError",
    "DeadKeyError",
    "resolve_key",
    "DEFAULT_BASE_URL",
    "KEY_ENV_VARS",
    "TRAFFIC_ROUTE_TYPE",
]


class CarRoutingClient:
    """Travel time and distance by car, from 2GIS, with live traffic.

    Usable as a context manager so the underlying connection pool is closed::

        with CarRoutingClient() as client:
            client.route(a, b)

    For an event loop, use :class:`car_routing.AsyncCarRoutingClient` instead.
    """

    def __init__(
        self,
        key: str | None = None,
        *,
        locale: str = "ru",
        route_type: str = TRAFFIC_ROUTE_TYPE,
        allow_locked_roads: bool = True,
        timeout: float = 20.0,
        max_workers: int = 8,
        max_retries: int = 3,
        base_url: str = DEFAULT_BASE_URL,
        headers: dict[str, str] | None = None,
        extra_body: dict[str, Any] | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        self.key = resolve_key(key)
        self.locale = locale
        self.route_type = route_type
        self.allow_locked_roads = allow_locked_roads
        self.max_workers = max(1, max_workers)
        self.max_retries = max(0, max_retries)
        self.base_url = base_url
        self.extra_body = dict(extra_body or {})

        # The endpoint is CORS-open (access-control-allow-origin: *) and needs
        # no auth beyond the key, but it is served to a browser, so we look
        # like one. Override via headers= if you prefer not to.
        self._headers = {**BROWSER_HEADERS, **(headers or {})}
        self._owns_client = client is None
        self._client = client or httpx.Client(
            timeout=timeout,
            headers=self._headers,
            limits=httpx.Limits(max_connections=self.max_workers * 2),
        )

    # -- lifecycle ---------------------------------------------------------

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> CarRoutingClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    # -- single routes -----------------------------------------------------

    def alternatives(self, origin: Any, destination: Any) -> list[Route]:
        """Every route the server offers, fastest first."""
        a, b = Point.coerce(origin), Point.coerce(destination)
        payload = self._post(
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

    def route(self, origin: Any, destination: Any) -> Route:
        """The fastest route. This is the one you usually want."""
        return self.alternatives(origin, destination)[0]

    # -- matrix ------------------------------------------------------------

    def matrix(
        self,
        origins: Iterable[Any],
        destinations: Iterable[Any] | None = None,
    ) -> DistanceMatrix:
        """Time and distance for every origin-destination pair.

        Pass one list for an all-pairs matrix, or two for a rectangular one.
        Pairs are fetched concurrently (``max_workers`` at a time); a pair whose
        own request fails gets ``error`` set on its cell rather than sinking the
        whole matrix.

        Note this endpoint has no batch mode, so an n x m matrix costs n * m
        requests. Identical origin/destination pairs are answered as zeroes
        without a call.
        """
        from_points = Point.coerce_all(origins)
        to_points = (
            from_points if destinations is None else Point.coerce_all(destinations)
        )

        if not from_points or not to_points:
            raise CarRoutingError("matrix() needs at least one origin and destination")

        pairs = [
            (i, j)
            for i in range(len(from_points))
            for j in range(len(to_points))
            if not same_place(from_points[i], to_points[j])
        ]

        cells: dict[tuple[int, int], MatrixCell] = {
            (i, j): MatrixCell(origin=i, destination=j, distance_m=0, duration_s=0)
            for i in range(len(from_points))
            for j in range(len(to_points))
        }

        if pairs:
            workers = min(self.max_workers, len(pairs))
            with ThreadPoolExecutor(max_workers=workers) as pool:
                results = pool.map(
                    lambda ij: self._one_cell(
                        from_points[ij[0]], to_points[ij[1]], *ij
                    ),
                    pairs,
                )
                for cell in results:
                    cells[(cell.origin, cell.destination)] = cell

        return DistanceMatrix(
            origins=from_points,
            destinations=to_points,
            cells=[
                [cells[(i, j)] for j in range(len(to_points))]
                for i in range(len(from_points))
            ],
        )

    def _one_cell(self, a: Point, b: Point, i: int, j: int) -> MatrixCell:
        try:
            best = self.route(a, b)
        except CarRoutingError as exc:
            return MatrixCell(origin=i, destination=j, error=str(exc))
        return MatrixCell(
            origin=i,
            destination=j,
            distance_m=best.distance_m,
            duration_s=best.duration_s,
        )

    # -- transport ---------------------------------------------------------

    def _post(self, body: dict[str, Any]) -> Any:
        last_error: Exception | None = None

        for attempt in range(self.max_retries + 1):
            if attempt:
                time.sleep(backoff_seconds(attempt))
            try:
                response = self._client.post(
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
