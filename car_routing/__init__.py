"""Python client for 2GIS car routing: travel time and distance, with live traffic.

Wraps the endpoint the 2gis.kz web app uses::

    POST https://routing.api.2gis.com/carrouting/6.0.0/global?key=...

Only ``total_distance`` (metres) and ``total_duration`` (seconds) are read from
the response; geometry, manoeuvres and congestion colours are ignored.

Quick start::

    from car_routing import CarRoutingClient, Point

    with CarRoutingClient() as client:                  # key from the env
        leg = client.route((76.917284, 43.239218),      # (lon, lat)
                           (76.9575, 43.244608))
        print(leg)                                      # "15.2 min / 3.57 km"

        m = client.matrix([(76.917284, 43.239218),
                           (76.9575, 43.244608),
                           (76.8895, 43.2385)])
        print(m.format_table("duration_min"))

Requires ``httpx`` and ``pydantic>=2``.
"""

from .env import load_env, parse_env
from .client import (
    DEFAULT_BASE_URL,
    KEY_ENV_VARS,
    TRAFFIC_ROUTE_TYPE,
    CarRoutingClient,
    CarRoutingError,
    DeadKeyError,
    resolve_key,
)
from .models import DistanceMatrix, MatrixCell, Point, Route

__all__ = [
    "CarRoutingClient",
    "CarRoutingError",
    "DeadKeyError",
    "DistanceMatrix",
    "MatrixCell",
    "Point",
    "Route",
    "resolve_key",
    "load_env",
    "parse_env",
    "DEFAULT_BASE_URL",
    "KEY_ENV_VARS",
    "TRAFFIC_ROUTE_TYPE",
]
