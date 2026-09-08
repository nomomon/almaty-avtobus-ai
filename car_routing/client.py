"""HTTP client for the 2GIS car routing endpoint."""

from __future__ import annotations

import os
import random
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Iterable

import httpx
from pydantic import BaseModel, ConfigDict, Field

from .models import DistanceMatrix, MatrixCell, Point, Route

DEFAULT_BASE_URL = "https://routing.api.2gis.com/carrouting/6.0.0/global"

#: Env vars consulted for the API key, in order.
KEY_ENV_VARS = ("TWOGIS_ROUTING_KEY", "TWOGIS_API_KEY", "2GIS_API_KEY")

#: Only value confirmed to work. "online5" is the live-traffic mode; the web
#: app uses it for its "с учётом пробок" routes.
TRAFFIC_ROUTE_TYPE = "online5"

_RETRY_STATUSES = frozenset({408, 425, 429, 500, 502, 503, 504})


class CarRoutingError(RuntimeError):
    """Any failed call. ``status`` and ``body`` are set when we got a response."""

    def __init__(
        self, message: str, *, status: int | None = None, body: str | None = None
    ) -> None:
        super().__init__(message)
        self.status = status
        self.body = body


class DeadKeyError(CarRoutingError):
    """The API key was rejected.

    2GIS answers a bad, revoked, or unprovisioned key with HTTP 403 and
    ``{"type": "forbidden", "message": "invalid_request"}`` -- the same shape it
    uses for a malformed body, so this is raised for both. If the request
    worked yesterday and fails today with nothing changed, the key is gone:
    issue your own at dev.2gis.com (Directions API) and set one of
    TWOGIS_ROUTING_KEY / TWOGIS_API_KEY / 2GIS_API_KEY.
    """


class _RawRoute(BaseModel):
    model_config = ConfigDict(extra="ignore")

    total_distance: int = Field(ge=0)
    total_duration: int = Field(ge=0)
    algorithm: str | None = None
    route_id: str | None = None

    def to_route(self) -> Route:
        return Route(
            distance_m=self.total_distance,
            duration_s=self.total_duration,
            algorithm=self.algorithm,
            route_id=self.route_id,
        )


class _RawResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    message: str | None = None
    result: list[_RawRoute] = Field(default_factory=list)


def resolve_key(key: str | None = None) -> str:
    """Return an explicit key, else the first one found in the environment."""
    if key:
        return key
    for name in KEY_ENV_VARS:
        found = os.environ.get(name)
        if found:
            return found
    raise CarRoutingError(
        "No 2GIS API key. Pass key=... or set one of: "
        + ", ".join(KEY_ENV_VARS)
        + ". Get one at dev.2gis.com (Directions API)."
    )


class CarRoutingClient:
    """Travel time and distance by car, from 2GIS, with live traffic.

    Usable as a context manager so the underlying connection pool is closed::

        with CarRoutingClient() as client:
            client.route(a, b)
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
        self._headers = {
            "content-type": "application/json",
            "accept": "application/json, text/plain, */*",
            "referer": "https://2gis.kz/",
            "user-agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/152.0.0.0 Safari/537.36"
            ),
            **(headers or {}),
        }
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
        payload = self._post(self._build_body(a, b))
        parsed = _RawResponse.model_validate(payload)

        if not parsed.result:
            raise CarRoutingError(
                "No route between "
                f"({a.lon}, {a.lat}) and ({b.lon}, {b.lat})"
                + (f": {parsed.message}" if parsed.message else "")
            )
        return sorted(
            (raw.to_route() for raw in parsed.result), key=lambda r: r.duration_s
        )

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
        to_points = from_points if destinations is None else Point.coerce_all(destinations)

        if not from_points or not to_points:
            raise CarRoutingError("matrix() needs at least one origin and destination")

        pairs = [
            (i, j)
            for i in range(len(from_points))
            for j in range(len(to_points))
            if not self._same_place(from_points[i], to_points[j])
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
                    lambda ij: self._one_cell(from_points[ij[0]], to_points[ij[1]], *ij),
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

    @staticmethod
    def _same_place(a: Point, b: Point, tolerance: float = 1e-6) -> bool:
        return abs(a.lon - b.lon) < tolerance and abs(a.lat - b.lat) < tolerance

    # -- transport ---------------------------------------------------------

    def _build_body(self, a: Point, b: Point) -> dict[str, Any]:
        # Field set copied from the 2gis.kz web app. A trimmed body (no
        # `viewport`, no `need_immersion`, no point names) came back as
        # {"type": "forbidden", "message": "invalid_request"}; which of them is
        # the mandatory one was never isolated, so send the lot even though
        # only the totals are read back.
        #
        # One deviation from the captured request: the app also sends an
        # `object_id` per point (a catalog POI id it has because the user
        # clicked a POI). Arbitrary coordinates have no such id, so it is
        # omitted -- the only part of this body not confirmed against a live
        # 200. If calls start failing with `invalid_request`, suspect this
        # first.
        return {
            "locale": self.locale,
            "point_a_name": a.name,
            "point_b_name": b.name,
            "points": [
                {"type": "pedo", "x": a.lon, "y": a.lat},
                {"type": "pedo", "x": b.lon, "y": b.lat},
            ],
            "purpose": "autoSearch",
            "type": self.route_type,
            "extended_colors": True,
            "viewport": {
                "topLeft": {"x": min(a.lon, b.lon), "y": max(a.lat, b.lat)},
                "bottomRight": {"x": max(a.lon, b.lon), "y": min(a.lat, b.lat)},
                "zoom": 13.5,
            },
            "need_immersion": True,
            "allow_locked_roads": self.allow_locked_roads,
            **self.extra_body,
        }

    def _post(self, body: dict[str, Any]) -> Any:
        last_error: Exception | None = None

        for attempt in range(self.max_retries + 1):
            if attempt:
                time.sleep(min(2.0**attempt, 8.0) * (0.5 + random.random()))
            try:
                response = self._client.post(
                    self.base_url, params={"key": self.key}, json=body
                )
            except httpx.HTTPError as exc:
                last_error = CarRoutingError(f"request failed: {exc}")
                continue

            if response.status_code in _RETRY_STATUSES:
                last_error = CarRoutingError(
                    f"HTTP {response.status_code} from 2GIS",
                    status=response.status_code,
                    body=response.text[:300],
                )
                continue

            if response.status_code == 403:
                raise DeadKeyError(
                    f"2GIS rejected the request (HTTP 403): {response.text[:200]}. "
                    "Either the key is dead or the body is malformed; see "
                    "DeadKeyError's docstring.",
                    status=403,
                    body=response.text[:300],
                )

            if response.status_code >= 400:
                raise CarRoutingError(
                    f"HTTP {response.status_code} from 2GIS: {response.text[:200]}",
                    status=response.status_code,
                    body=response.text[:300],
                )

            try:
                return response.json()
            except ValueError as exc:
                raise CarRoutingError(
                    f"2GIS returned invalid JSON: {exc}",
                    status=response.status_code,
                    body=response.text[:300],
                ) from exc

        raise last_error or CarRoutingError("request failed for an unknown reason")
