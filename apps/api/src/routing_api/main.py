"""FastAPI app: car travel time and distance, point to point or as a matrix."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from car_routing import AsyncCarRoutingClient, CarRoutingError, DeadKeyError, Point
from fastapi import Depends, FastAPI, HTTPException, Query, Request, status

from .cache import RouteCache, make_backend
from .config import Settings, get_settings
from .schemas import (
    HealthResponse,
    MatrixFailure,
    MatrixMeta,
    MatrixRequest,
    MatrixResponse,
    PointIn,
    RouteRequest,
    RouteResponse,
)
from .service import RoutingService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

#: Starlette renamed its 422 constant; the number is the stable part.
UNPROCESSABLE = 422

#: Placeholder so the app can boot (and report the problem on /health) with no
#: key configured. Requests are refused by require_key before it is ever sent.
MISSING_KEY_SENTINEL = "unset"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()

    key = settings.resolved_key()
    if not key:
        # Deliberately not fatal: /health should be able to report the problem
        # rather than the container crash-looping before anyone can ask.
        logger.error(
            "no 2GIS key configured; routing will fail until one of "
            "TWOGIS_ROUTING_KEY / TWOGIS_API_KEY / 2GIS_API_KEY is set"
        )

    backend = await make_backend(settings.redis_url)
    client = AsyncCarRoutingClient(
        key=key or MISSING_KEY_SENTINEL,
        timeout=settings.upstream_timeout_s,
        max_concurrency=settings.upstream_max_concurrency,
        max_retries=settings.upstream_max_retries,
    )
    cache = RouteCache(
        backend,
        ttl_s=settings.cache_ttl_s,
        prefix=settings.cache_prefix,
        coord_precision=settings.cache_coord_precision,
        route_type=client.route_type,
    )

    app.state.settings = settings
    app.state.has_key = bool(key)
    app.state.cache = cache
    app.state.service = RoutingService(client, cache)
    try:
        yield
    finally:
        await client.aclose()
        close = getattr(backend, "aclose", None) or getattr(backend, "close", None)
        if close is not None:
            try:
                result = close()
                if hasattr(result, "__await__"):
                    await result
            except Exception as exc:
                logger.warning("error closing cache connection: %s", exc)


app = FastAPI(
    title="Almaty car routing",
    version="0.1.0",
    summary="Travel time and distance by car from 2GIS, cached.",
    lifespan=lifespan,
)


def get_service(request: Request) -> RoutingService:
    service = getattr(request.app.state, "service", None)
    if service is None:  # pragma: no cover - only if lifespan did not run
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "service is still starting"
        )
    return service


def require_key(request: Request) -> None:
    """Refuse routing when no upstream key is configured.

    Without this the request goes out with a placeholder key and 2GIS answers
    403, which surfaces as "the key was probably rotated" -- exactly the wrong
    thing to tell someone who simply has not set one yet.
    """
    if not getattr(request.app.state, "has_key", False):
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "No 2GIS API key configured. Set TWOGIS_ROUTING_KEY (or "
            "TWOGIS_API_KEY / 2GIS_API_KEY) in the service environment and "
            "restart. /health reports this as upstream_key: missing.",
        )


ServiceDep = Annotated[RoutingService, Depends(get_service)]
KeyRequired = Depends(require_key)
SettingsDep = Annotated[Settings, Depends(get_settings)]


def _to_point(value: PointIn) -> Point:
    return Point(lon=value.lon, lat=value.lat)


def _parse_pair(raw: str, field: str) -> Point:
    """Read a ``lon,lat`` query parameter."""
    parts = raw.split(",")
    if len(parts) != 2:
        raise HTTPException(
            UNPROCESSABLE,
            f"{field} must be 'lon,lat', got {raw!r}",
        )
    try:
        return Point(lon=float(parts[0]), lat=float(parts[1]))
    except (ValueError, TypeError) as exc:
        raise HTTPException(
            UNPROCESSABLE, f"{field} is not a valid point: {exc}"
        ) from exc


def _upstream_error(exc: CarRoutingError) -> HTTPException:
    """Translate an upstream failure into something a caller can act on."""
    if isinstance(exc, DeadKeyError):
        return HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            "2GIS rejected our API key. It was probably rotated; see the "
            "service logs and replace it.",
        )
    if exc.status == 429:
        return HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS, "rate limited by 2GIS, retry later"
        )
    if "No route" in str(exc):
        return HTTPException(status.HTTP_404_NOT_FOUND, str(exc))
    return HTTPException(status.HTTP_502_BAD_GATEWAY, f"upstream failure: {exc}")


@app.get("/health", response_model=HealthResponse, tags=["meta"])
async def health(request: Request) -> HealthResponse:
    cache: RouteCache | None = getattr(request.app.state, "cache", None)
    if cache is None:
        cache_state = "unavailable"
    elif cache.backend is None:
        cache_state = "unavailable"
    elif not cache.enabled:
        cache_state = "disabled"
    else:
        cache_state = "ready"

    return HealthResponse(
        status="ok",
        cache=cache_state,
        upstream_key=(
            "configured" if getattr(request.app.state, "has_key", False) else "missing"
        ),
    )


@app.post(
    "/v1/route",
    response_model=RouteResponse,
    tags=["routing"],
    dependencies=[KeyRequired],
)
async def post_route(body: RouteRequest, service: ServiceDep) -> RouteResponse:
    """Travel time and distance between two points, by car, with traffic."""
    return await _route(service, _to_point(body.origin), _to_point(body.destination))


@app.get(
    "/v1/route",
    response_model=RouteResponse,
    tags=["routing"],
    dependencies=[KeyRequired],
)
async def get_route(
    service: ServiceDep,
    origin: Annotated[
        str, Query(description="lon,lat", examples=["76.917284,43.239218"])
    ],
    destination: Annotated[
        str, Query(description="lon,lat", examples=["76.9575,43.244608"])
    ],
) -> RouteResponse:
    """Same as POST /v1/route, for quick curl-ing."""
    return await _route(
        service, _parse_pair(origin, "origin"), _parse_pair(destination, "destination")
    )


async def _route(service: RoutingService, a: Point, b: Point) -> RouteResponse:
    try:
        route, cached = await service.route(a, b)
    except CarRoutingError as exc:
        raise _upstream_error(exc) from exc

    return RouteResponse(
        distance_m=route.distance_m,
        duration_s=route.duration_s,
        distance_km=route.distance_km,
        duration_min=route.duration_min,
        mean_speed_kmh=route.mean_speed_kmh,
        traffic_aware=route.traffic_aware,
        cached=cached,
    )


@app.post(
    "/v1/matrix",
    response_model=MatrixResponse,
    tags=["routing"],
    dependencies=[KeyRequired],
)
async def post_matrix(
    body: MatrixRequest, service: ServiceDep, settings: SettingsDep
) -> MatrixResponse:
    """Time and distance for every origin-destination pair.

    ``durations_s[i][j]`` is origins[i] -> destinations[j], with the diagonal
    zeroed for identical points. A pair that fails is ``null`` in the grids and
    listed in ``failures``, so one bad pair does not lose the rest.

    Costs one upstream request per uncached pair, hence the size limits.
    """
    origins = [_to_point(p) for p in body.origins]
    destinations = (
        None if body.destinations is None else [_to_point(p) for p in body.destinations]
    )

    n_from, n_to = len(origins), len(destinations or origins)
    if max(n_from, n_to) > settings.max_points_per_side:
        raise HTTPException(
            UNPROCESSABLE,
            f"at most {settings.max_points_per_side} points per side, "
            f"got {n_from} origins and {n_to} destinations",
        )
    if n_from * n_to > settings.max_matrix_pairs:
        raise HTTPException(
            UNPROCESSABLE,
            f"{n_from} x {n_to} = {n_from * n_to} pairs exceeds the limit of "
            f"{settings.max_matrix_pairs}; each uncached pair is one upstream call",
        )

    try:
        outcome = await service.matrix(origins, destinations)
    except CarRoutingError as exc:
        raise _upstream_error(exc) from exc

    return MatrixResponse(
        durations_s=outcome.durations_s,
        distances_m=outcome.distances_m,
        failures=[
            MatrixFailure(origin=i, destination=j, error=error)
            for i, j, error in outcome.failures
        ],
        meta=MatrixMeta(
            pairs=outcome.pairs,
            from_cache=outcome.from_cache,
            fetched=outcome.fetched,
            trivial=outcome.trivial,
            failed=len(outcome.failures),
            elapsed_ms=outcome.elapsed_ms,
        ),
    )
