"""Client for 2GIS car routing: travel time and distance, with live traffic.

Wraps the endpoint the 2gis.kz web app uses::

    POST https://routing.api.2gis.com/carrouting/6.0.0/global?key=...

Only ``total_distance`` (metres) and ``total_duration`` (seconds) are read from
the response; geometry, manoeuvres and congestion colours are ignored.

Sync::

    from car_routing import CarRoutingClient

    with CarRoutingClient() as client:                  # key from the env
        print(client.route((76.917284, 43.239218),      # (lon, lat)
                           (76.9575, 43.244608)))       # "15.2 min / 3.57 km"
        print(client.matrix(stops).durations_min)

Async, for an event loop::

    from car_routing import AsyncCarRoutingClient

    async with AsyncCarRoutingClient() as client:
        route = await client.route(a, b)
        matrix = await client.matrix(stops)

Requires ``httpx`` and ``pydantic>=2``.
"""

from ._core import (
    DEFAULT_BASE_URL,
    KEY_ENV_VARS,
    TRAFFIC_ROUTE_TYPE,
    CarRoutingError,
    DeadKeyError,
    resolve_key,
)
from .aclient import AsyncCarRoutingClient
from .client import CarRoutingClient
from .env import load_env, parse_env
from .models import DistanceMatrix, MatrixCell, Point, Route
from .transit import (
    ALL_TRANSPORT,
    ALMATY_TRANSPORT,
    PEDESTRIAN,
    AsyncTransitClient,
    TransitClient,
    TransitRoute,
)

__all__ = [
    "AsyncCarRoutingClient",
    "AsyncTransitClient",
    "TransitClient",
    "TransitRoute",
    "ALL_TRANSPORT",
    "ALMATY_TRANSPORT",
    "PEDESTRIAN",
    "CarRoutingClient",
    "CarRoutingError",
    "DeadKeyError",
    "DistanceMatrix",
    "MatrixCell",
    "Point",
    "Route",
    "load_env",
    "parse_env",
    "resolve_key",
    "DEFAULT_BASE_URL",
    "KEY_ENV_VARS",
    "TRAFFIC_ROUTE_TYPE",
]
