"""Pieces shared by the sync and async clients: config, errors, wire format.

Everything here is transport-agnostic, so the two clients differ only in how
they move bytes.
"""

from __future__ import annotations

import os
import random
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .models import Point, Route

DEFAULT_BASE_URL = "https://routing.api.2gis.com/carrouting/6.0.0/global"

#: Env vars consulted for the API key, in order.
KEY_ENV_VARS = ("TWOGIS_ROUTING_KEY", "TWOGIS_API_KEY", "2GIS_API_KEY")

#: Only value confirmed to work. "online5" is the live-traffic mode; the web
#: app uses it for its "с учётом пробок" routes.
TRAFFIC_ROUTE_TYPE = "online5"

RETRY_STATUSES = frozenset({408, 425, 429, 500, 502, 503, 504})

BROWSER_HEADERS = {
    "content-type": "application/json",
    "accept": "application/json, text/plain, */*",
    "referer": "https://2gis.kz/",
    "user-agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36"
    ),
}


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


class RawRoute(BaseModel):
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


class RawResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    message: str | None = None
    result: list[RawRoute] = Field(default_factory=list)


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


def build_body(
    a: Point,
    b: Point,
    *,
    locale: str,
    route_type: str,
    allow_locked_roads: bool,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """The request body, shaped like the one 2gis.kz sends.

    A trimmed body (no ``viewport``, no ``need_immersion``, no point names)
    comes back as ``{"type": "forbidden", "message": "invalid_request"}``; which
    of them is the mandatory one was never isolated, so send the lot even
    though only the totals are read back.

    One deviation from the captured request: the app also sends an
    ``object_id`` per point (a catalog POI id it has because the user clicked a
    POI). Arbitrary coordinates have no such id, so it is omitted -- the only
    part of this body not confirmed against a live 200. If calls start failing
    with ``invalid_request``, suspect this first.
    """
    return {
        "locale": locale,
        "point_a_name": a.name,
        "point_b_name": b.name,
        "points": [
            {"type": "pedo", "x": a.lon, "y": a.lat},
            {"type": "pedo", "x": b.lon, "y": b.lat},
        ],
        "purpose": "autoSearch",
        "type": route_type,
        "extended_colors": True,
        "viewport": {
            "topLeft": {"x": min(a.lon, b.lon), "y": max(a.lat, b.lat)},
            "bottomRight": {"x": max(a.lon, b.lon), "y": min(a.lat, b.lat)},
            "zoom": 13.5,
        },
        "need_immersion": True,
        "allow_locked_roads": allow_locked_roads,
        **(extra or {}),
    }


def parse_routes(payload: Any, a: Point, b: Point) -> list[Route]:
    """Turn a 200 body into routes, fastest first."""
    parsed = RawResponse.model_validate(payload)
    if not parsed.result:
        raise CarRoutingError(
            f"No route between ({a.lon}, {a.lat}) and ({b.lon}, {b.lat})"
            + (f": {parsed.message}" if parsed.message else "")
        )
    return sorted((raw.to_route() for raw in parsed.result), key=lambda r: r.duration_s)


def check_status(status: int, text: str) -> CarRoutingError | None:
    """Map a non-retryable failure onto an exception, or None if the response
    is fine. Retryable statuses are the caller's business."""
    if status == 403:
        return DeadKeyError(
            f"2GIS rejected the request (HTTP 403): {text[:200]}. Either the key "
            "is dead or the body is malformed; see DeadKeyError's docstring.",
            status=403,
            body=text[:300],
        )
    if status >= 400:
        return CarRoutingError(
            f"HTTP {status} from 2GIS: {text[:200]}", status=status, body=text[:300]
        )
    return None


def backoff_seconds(attempt: int) -> float:
    """Exponential backoff with jitter, capped, for retry number ``attempt``."""
    return min(2.0**attempt, 8.0) * (0.5 + random.random())


def same_place(a: Point, b: Point, tolerance: float = 1e-6) -> bool:
    return abs(a.lon - b.lon) < tolerance and abs(a.lat - b.lat) < tolerance
