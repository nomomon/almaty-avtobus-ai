"""Public transport and walking routes, via 2GIS's ``ctx/2.0`` router.

    POST https://routing.api.2gis.com/ctx/2.0/{city}?key=...

Request shape is copied verbatim from a captured 2gis.kz session (the transit
and pedestrian tabs both drive this endpoint; ``pedestrian`` is one of the
transport modes it accepts).

IMPORTANT -- the response schema here is NOT confirmed. The capture contained
requests only, no response bodies, so the models below are deliberately
lenient: known-looking fields are lifted if present, and the untouched payload
is always kept on ``TransitRoute.raw``. Run ``scripts/dump_transit.py`` against
a live key to capture a real response, and these can become strict.

The documented, supported alternative is
``routing.api.2gis.com/public_transport/2.0``.
"""

from __future__ import annotations

import time
from collections.abc import Iterable, Sequence
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, Field

from ._core import (
    BROWSER_HEADERS,
    RETRY_STATUSES,
    TRAFFIC_ROUTE_TYPE,
    CarRoutingError,
    backoff_seconds,
    check_status,
    resolve_key,
)
from .models import Point

__all__ = [
    "ALL_TRANSPORT",
    "PEDESTRIAN",
    "AsyncTransitClient",
    "TransitClient",
    "TransitRoute",
    "parse_transit",
]

TRANSIT_BASE_URL = "https://routing.api.2gis.com/ctx/2.0"
FILTERS_BASE_URL = "https://routing.api.2gis.com/ctx/filters"

#: Every mode the captured request asked for, in its original order.
ALL_TRANSPORT: tuple[str, ...] = (
    "bus",
    "trolleybus",
    "tram",
    "shuttle_bus",
    "metro",
    "suburban_train",
    "funicular_railway",
    "monorail",
    "river_transport",
    "cable_car",
    "light_rail",
    "premetro",
    "light_metro",
    "aeroexpress",
    "pedestrian",
    "mcc",
    "mcd",
)

#: Walking only. The pedestrian tab on 2gis.kz is this endpoint with the
#: pedestrian mode; asking for it alone is inference, not captured fact.
PEDESTRIAN: tuple[str, ...] = ("pedestrian",)

#: Modes that actually exist in Almaty, to keep requests honest.
ALMATY_TRANSPORT: tuple[str, ...] = (
    "bus",
    "trolleybus",
    "tram",
    "shuttle_bus",
    "metro",
    "suburban_train",
    "pedestrian",
)


class TransitRoute(BaseModel):
    """One itinerary. Lenient on purpose -- see the module docstring.

    ``raw`` always holds the untouched upstream object, so nothing is lost
    while the schema is still being pinned down.
    """

    model_config = ConfigDict(extra="allow")

    total_duration_s: int | None = Field(default=None, ge=0)
    total_distance_m: int | None = Field(default=None, ge=0)
    total_walkway_distance_m: int | None = Field(default=None, ge=0)
    transfer_count: int | None = Field(default=None, ge=0)
    crossing_count: int | None = Field(default=None, ge=0)
    route_ids: list[str] = Field(default_factory=list)
    raw: dict[str, Any] = Field(default_factory=dict, repr=False)

    @property
    def duration_min(self) -> float | None:
        if self.total_duration_s is None:
            return None
        return round(self.total_duration_s / 60.0, 1)

    @property
    def distance_km(self) -> float | None:
        if self.total_distance_m is None:
            return None
        return round(self.total_distance_m / 1000.0, 2)

    def __str__(self) -> str:
        parts = []
        if self.duration_min is not None:
            parts.append(f"{self.duration_min} min")
        if self.distance_km is not None:
            parts.append(f"{self.distance_km} km")
        if self.transfer_count is not None:
            parts.append(f"{self.transfer_count} transfers")
        return " / ".join(parts) or "route (unparsed, see .raw)"


def _first_int(source: dict[str, Any], *names: str) -> int | None:
    """First present, int-coercible value among ``names``."""
    for name in names:
        value = source.get(name)
        if isinstance(value, bool):
            continue
        if isinstance(value, (int, float)):
            return int(value)
        if isinstance(value, str) and value.strip().lstrip("-").isdigit():
            return int(value)
    return None


def _route_ids(source: dict[str, Any]) -> list[str]:
    """Pull public-transport route names/numbers out, wherever they hide.

    Shapes vary between 2GIS endpoints, so this looks for the usual suspects
    rather than assuming one.
    """
    found: list[str] = []

    def walk(node: Any, depth: int = 0) -> None:
        if depth > 6:
            return
        if isinstance(node, dict):
            for key in ("route_number", "route_name", "name", "number"):
                value = node.get(key)
                if isinstance(value, (str, int)) and str(value).strip():
                    text = str(value).strip()
                    if text not in found:
                        found.append(text)
                    break
            for key in ("movements", "routes", "legs", "passages", "route"):
                if key in node:
                    walk(node[key], depth + 1)
        elif isinstance(node, list):
            for item in node[:40]:
                walk(item, depth + 1)

    for key in ("movements", "routes", "legs"):
        if key in source:
            walk(source[key])
    return found


def parse_transit(payload: Any) -> list[TransitRoute]:
    """Read routes out of a ctx/2.0 response, whatever it turns out to be.

    Handles a bare list, ``{"result": [...]}`` and ``{"routes": [...]}``, and
    keeps every object it cannot interpret rather than dropping it.
    """
    if isinstance(payload, dict):
        for key in ("result", "routes", "items", "data"):
            if isinstance(payload.get(key), list):
                items = payload[key]
                break
        else:
            items = [payload]
    elif isinstance(payload, list):
        items = payload
    else:
        raise CarRoutingError(f"unexpected transit payload: {type(payload).__name__}")

    routes: list[TransitRoute] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        routes.append(
            TransitRoute(
                total_duration_s=_first_int(
                    item, "total_duration", "duration", "total_time"
                ),
                total_distance_m=_first_int(item, "total_distance", "distance"),
                total_walkway_distance_m=_first_int(
                    item, "total_walkway_distance", "walkway_distance"
                ),
                transfer_count=_first_int(item, "transfer_count", "transfers"),
                crossing_count=_first_int(item, "crossing_count"),
                route_ids=_route_ids(item),
                raw=item,
            )
        )

    if not routes:
        raise CarRoutingError("no transit routes in the response")

    routes.sort(key=lambda r: (r.total_duration_s is None, r.total_duration_s or 0))
    return routes


def build_transit_body(
    source: Point,
    target: Point,
    *,
    transport: Sequence[str],
    locale: str = "ru",
    start_time: int | None = None,
    enable_schedule: bool = True,
    group_by_route: bool = True,
) -> dict[str, Any]:
    """The ctx/2.0 body, shaped like the captured one.

    ``start_time`` is a unix timestamp for "depart at"; it defaults to now,
    which is what the web app sends.
    """
    if not transport:
        raise CarRoutingError("transport must name at least one mode")

    return {
        "locale": locale,
        "enable_schedule": enable_schedule,
        "source": {
            "point": {"lat": source.lat, "lon": source.lon},
            "name": source.name,
        },
        "target": {
            "point": {"lat": target.lat, "lon": target.lon},
            "name": target.name,
        },
        "transport": list(transport),
        "purpose": "routeSearch",
        "viewport": {
            "topLeft": {
                "x": min(source.lon, target.lon),
                "y": max(source.lat, target.lat),
            },
            "bottomRight": {
                "x": max(source.lon, target.lon),
                "y": min(source.lat, target.lat),
            },
            "zoom": 13.25,
        },
        "start_time": int(start_time if start_time is not None else time.time()),
        "need_immersion": True,
        "group_by_route": group_by_route,
    }


class _TransitBase:
    def __init__(
        self,
        key: str | None = None,
        *,
        city: str = "almaty",
        locale: str = "ru",
        timeout: float = 20.0,
        max_retries: int = 3,
        base_url: str = TRANSIT_BASE_URL,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.key = resolve_key(key)
        self.city = city
        self.locale = locale
        self.max_retries = max(0, max_retries)
        self.base_url = base_url
        self.timeout = timeout
        self._headers = {**BROWSER_HEADERS, **(headers or {})}

    @property
    def url(self) -> str:
        return f"{self.base_url}/{self.city}"

    def _body(
        self,
        origin: Any,
        destination: Any,
        transport: Sequence[str],
        start_time: int | None,
    ) -> dict[str, Any]:
        return build_transit_body(
            Point.coerce(origin),
            Point.coerce(destination),
            transport=transport,
            locale=self.locale,
            start_time=start_time,
        )


class TransitClient(_TransitBase):
    """Public transport and walking routes, synchronous.

    ::

        with TransitClient() as client:
            for route in client.transit(a, b):        # buses, trams, metro
                print(route, route.route_ids)
            print(client.walk(a, b)[0])               # walking only
    """

    def __init__(self, *args: Any, client: httpx.Client | None = None, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self._owns_client = client is None
        self._client = client or httpx.Client(
            timeout=self.timeout, headers=self._headers
        )

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> TransitClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def routes(
        self,
        origin: Any,
        destination: Any,
        *,
        transport: Iterable[str] = ALMATY_TRANSPORT,
        start_time: int | None = None,
    ) -> list[TransitRoute]:
        """Itineraries for the given modes, shortest duration first."""
        body = self._body(origin, destination, tuple(transport), start_time)
        return parse_transit(self._post(body))

    def transit(
        self, origin: Any, destination: Any, *, start_time: int | None = None
    ) -> list[TransitRoute]:
        """Public transport (walking legs included, as the app does it)."""
        return self.routes(
            origin, destination, transport=ALMATY_TRANSPORT, start_time=start_time
        )

    def walk(
        self, origin: Any, destination: Any, *, start_time: int | None = None
    ) -> list[TransitRoute]:
        """Walking only.

        Inferred from the pedestrian tab using this endpoint with the
        ``pedestrian`` mode; not separately captured.
        """
        return self.routes(
            origin, destination, transport=PEDESTRIAN, start_time=start_time
        )

    def filters(self) -> Any:
        """Whatever ``ctx/filters/{city}`` returns for an empty body."""
        return self._post({}, url=f"{FILTERS_BASE_URL}/{self.city}")

    def _post(self, body: dict[str, Any], url: str | None = None) -> Any:
        last_error: Exception | None = None
        target = url or self.url

        for attempt in range(self.max_retries + 1):
            if attempt:
                time.sleep(backoff_seconds(attempt))
            try:
                response = self._client.post(
                    target, params={"key": self.key}, json=body
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


class AsyncTransitClient(_TransitBase):
    """Public transport and walking routes, awaitable."""

    def __init__(
        self, *args: Any, client: httpx.AsyncClient | None = None, **kwargs: Any
    ):
        super().__init__(*args, **kwargs)
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            timeout=self.timeout, headers=self._headers
        )

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> AsyncTransitClient:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.aclose()

    async def routes(
        self,
        origin: Any,
        destination: Any,
        *,
        transport: Iterable[str] = ALMATY_TRANSPORT,
        start_time: int | None = None,
    ) -> list[TransitRoute]:
        body = self._body(origin, destination, tuple(transport), start_time)
        return parse_transit(await self._post(body))

    async def transit(
        self, origin: Any, destination: Any, *, start_time: int | None = None
    ) -> list[TransitRoute]:
        return await self.routes(
            origin, destination, transport=ALMATY_TRANSPORT, start_time=start_time
        )

    async def walk(
        self, origin: Any, destination: Any, *, start_time: int | None = None
    ) -> list[TransitRoute]:
        return await self.routes(
            origin, destination, transport=PEDESTRIAN, start_time=start_time
        )

    async def _post(self, body: dict[str, Any], url: str | None = None) -> Any:
        import asyncio

        last_error: Exception | None = None
        target = url or self.url

        for attempt in range(self.max_retries + 1):
            if attempt:
                await asyncio.sleep(backoff_seconds(attempt))
            try:
                response = await self._client.post(
                    target, params={"key": self.key}, json=body
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


# Keep the car route type importable from here too, so callers comparing the
# two endpoints do not need two imports.
CAR_ROUTE_TYPE = TRAFFIC_ROUTE_TYPE
