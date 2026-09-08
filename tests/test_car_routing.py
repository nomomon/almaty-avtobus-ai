"""Offline tests: models, matrix assembly, error handling.

The network is stubbed, so these check our own logic, not 2GIS. Run with
``python -m pytest tests`` (or ``python tests/test_car_routing.py`` for a
plain-assert run without pytest).

The one live check is at the bottom and is skipped unless a key is present.
"""

from __future__ import annotations

import os
import sys

import httpx
import pytest
from pydantic import ValidationError

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from car_routing import (  # noqa: E402
    CarRoutingClient,
    CarRoutingError,
    DeadKeyError,
    Point,
    Route,
)

A = (76.917284, 43.239218)
B = (76.9575, 43.244608)
C = (76.8895, 43.2385)

# Trimmed real response (2026-09-08, Almaty, A -> B).
LIVE_SAMPLE = {
    "message": None,
    "result": [
        {
            "algorithm": "с учётом пробок",
            "id": "6517997994209186365",
            "route_id": "kazakhstan-cr-back.m9/carrouting/1788878124.161774",
            "total_distance": 3571,
            "total_duration": 913,
            "ui_total_duration": "15 мин",
            "ui_total_distance": {"unit": "км", "value": "3.6"},
            "reliability": 0.0,
            "maneuvers": [],
            "waypoints": [],
        },
        {
            "algorithm": "с учётом пробок",
            "id": "16413336397843336655",
            "total_distance": 3752,
            "total_duration": 1019,
            "maneuvers": [],
        },
    ],
}


def make_client(handler, **kwargs) -> CarRoutingClient:
    transport = httpx.MockTransport(handler)
    return CarRoutingClient(
        key="test-key",
        client=httpx.Client(transport=transport),
        max_retries=kwargs.pop("max_retries", 0),
        **kwargs,
    )


def ok_handler(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, json=LIVE_SAMPLE)


# -- points -----------------------------------------------------------------


def test_point_coercion_reads_lon_lat_pairs():
    assert Point.coerce(A) == Point(lon=76.917284, lat=43.239218)
    assert Point.coerce({"lon": 1.0, "lat": 2.0}) == Point(lon=1.0, lat=2.0)
    assert Point.from_latlon(43.2, 76.9) == Point(lon=76.9, lat=43.2)


def test_point_rejects_out_of_range_and_bad_shapes():
    with pytest.raises(ValidationError):
        Point(lon=200.0, lat=43.0)
    with pytest.raises(ValidationError):
        Point(lon=76.9, lat=91.0)
    with pytest.raises(ValueError):
        Point.coerce((1.0, 2.0, 3.0))
    with pytest.raises(TypeError):
        Point.coerce("76.9,43.2")


def test_swapped_coordinates_are_caught_for_almaty():
    # A frequent mistake: passing (lat, lon). Almaty's latitude is a valid
    # longitude, so this one only fails on the latitude bound -- which it does.
    with pytest.raises(ValidationError):
        Point.coerce((43.239218, 176.917284))


# -- routes -----------------------------------------------------------------


def test_route_parses_and_derives_units():
    with make_client(ok_handler) as client:
        route = client.route(A, B)

    assert (route.distance_m, route.duration_s) == (3571, 913)
    assert route.distance_km == 3.57
    assert route.duration_min == 15.2  # matches the API's own "15 мин"
    assert route.mean_speed_kmh == 14.1
    assert route.traffic_aware is True
    assert str(route) == "15.2 min / 3.57 km"


def test_alternatives_are_sorted_fastest_first():
    with make_client(ok_handler) as client:
        routes = client.alternatives(A, B)

    assert [r.duration_s for r in routes] == [913, 1019]


def test_request_body_carries_the_fields_the_api_demands():
    seen: dict = {}

    def capture(request: httpx.Request) -> httpx.Response:
        import json

        seen.update(json.loads(request.content))
        seen["_key"] = request.url.params.get("key")
        return httpx.Response(200, json=LIVE_SAMPLE)

    with make_client(capture) as client:
        client.route(A, B)

    assert seen["_key"] == "test-key"
    assert seen["type"] == "online5"
    assert seen["points"] == [
        {"type": "pedo", "x": 76.917284, "y": 43.239218},
        {"type": "pedo", "x": 76.9575, "y": 43.244608},
    ]
    for required in ("viewport", "need_immersion", "point_a_name", "point_b_name"):
        assert required in seen, f"{required} must be sent or the API 403s"
    # viewport corners must bracket both points
    assert seen["viewport"]["topLeft"]["x"] <= seen["viewport"]["bottomRight"]["x"]
    assert seen["viewport"]["topLeft"]["y"] >= seen["viewport"]["bottomRight"]["y"]


def test_empty_result_is_an_error_not_an_empty_list():
    with make_client(lambda r: httpx.Response(200, json={"result": []})) as client:
        with pytest.raises(CarRoutingError, match="No route"):
            client.route(A, B)


# -- matrix -----------------------------------------------------------------


def test_all_pairs_matrix_shape_and_zero_diagonal():
    with make_client(ok_handler) as client:
        matrix = client.matrix([A, B, C])

    assert (len(matrix.origins), len(matrix.destinations)) == (3, 3)
    for i in range(3):
        assert matrix.cell(i, i).duration_s == 0
        assert matrix.cell(i, i).distance_m == 0
    assert matrix.durations_s[0][1] == 913
    assert matrix.distances_km[0][1] == 3.57
    assert matrix.failures == []


def test_rectangular_matrix():
    with make_client(ok_handler) as client:
        matrix = client.matrix([A, B], [B, C, A])

    assert (len(matrix.cells), len(matrix.cells[0])) == (2, 3)
    assert matrix.cell(0, 2).duration_s == 0  # A -> A
    assert matrix.cell(0, 0).duration_s == 913  # A -> B


def test_one_bad_pair_does_not_sink_the_matrix():
    calls = {"n": 0}

    def flaky(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(400, json={"message": "nope"})
        return httpx.Response(200, json=LIVE_SAMPLE)

    with make_client(flaky, max_workers=1) as client:
        matrix = client.matrix([A, B])

    assert len(matrix.failures) == 1
    failed = matrix.failures[0]
    assert failed.ok is False
    assert failed.duration_s is None
    assert "400" in failed.error
    # the other direction still came back
    assert matrix.cell(1, 0).duration_s == 913


def test_matrix_records_and_table_render():
    with make_client(ok_handler) as client:
        matrix = client.matrix([A, B])

    records = matrix.to_records()
    assert len(records) == 4
    assert records[1]["duration_s"] == 913
    assert records[1]["origin_lon"] == 76.917284
    assert "duration_min" in matrix.format_table("duration_min")
    with pytest.raises(ValueError):
        matrix.format_table("nonsense")


def test_matrix_needs_points():
    with make_client(ok_handler) as client:
        with pytest.raises(CarRoutingError, match="at least one"):
            client.matrix([])


# -- keys and failures ------------------------------------------------------


def test_missing_key_names_the_env_vars(monkeypatch):
    for name in ("TWOGIS_ROUTING_KEY", "TWOGIS_API_KEY", "2GIS_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(CarRoutingError, match="TWOGIS_ROUTING_KEY"):
        CarRoutingClient()


def test_env_key_is_picked_up_in_order(monkeypatch):
    monkeypatch.delenv("TWOGIS_ROUTING_KEY", raising=False)
    monkeypatch.setenv("2GIS_API_KEY", "from-env")
    assert CarRoutingClient(client=httpx.Client()).key == "from-env"
    monkeypatch.setenv("TWOGIS_ROUTING_KEY", "preferred")
    assert CarRoutingClient(client=httpx.Client()).key == "preferred"


def test_403_raises_dead_key_error():
    def forbidden(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            403, json={"type": "forbidden", "message": "invalid_request"}
        )

    with make_client(forbidden) as client:
        with pytest.raises(DeadKeyError) as caught:
            client.route(A, B)

    assert caught.value.status == 403
    assert "invalid_request" in caught.value.body


def test_retries_then_succeeds():
    calls = {"n": 0}

    def rate_limited(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] < 3:
            return httpx.Response(429, text="slow down")
        return httpx.Response(200, json=LIVE_SAMPLE)

    client = make_client(rate_limited, max_retries=3)
    client._client.timeout = httpx.Timeout(1.0)
    with client:
        route = client.route(A, B)

    assert calls["n"] == 3
    assert route.duration_s == 913


def test_retries_give_up_and_report_the_status():
    with make_client(lambda r: httpx.Response(503, text="down"), max_retries=1) as c:
        with pytest.raises(CarRoutingError) as caught:
            c.route(A, B)

    assert caught.value.status == 503


def test_invalid_json_is_reported_clearly():
    with make_client(lambda r: httpx.Response(200, text="<html>")) as client:
        with pytest.raises(CarRoutingError, match="invalid JSON"):
            client.route(A, B)


# -- live smoke test --------------------------------------------------------


@pytest.mark.skipif(
    not any(os.environ.get(v) for v in ("TWOGIS_ROUTING_KEY", "2GIS_API_KEY")),
    reason="no 2GIS key in the environment",
)
def test_live_route_is_plausible():
    with CarRoutingClient() as client:
        route = client.route(A, B)

    assert 1000 < route.distance_m < 10_000
    assert 120 < route.duration_s < 3600
    assert route.mean_speed_kmh and 3 < route.mean_speed_kmh < 90


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
