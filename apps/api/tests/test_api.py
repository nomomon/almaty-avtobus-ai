"""API tests. Upstream is stubbed; the cache is a dict-backed fake."""

from __future__ import annotations

import httpx
import pytest
from car_routing import AsyncCarRoutingClient
from fastapi.testclient import TestClient
from routing_api.cache import RouteCache
from routing_api.config import Settings
from routing_api.main import app, get_service, get_settings
from routing_api.service import RoutingService

A = {"lon": 76.917284, "lat": 43.239218}
B = {"lon": 76.9575, "lat": 43.244608}
C = {"lon": 76.8895, "lat": 43.2385}

SAMPLE = {
    "result": [
        {
            "algorithm": "с учётом пробок",
            "total_distance": 3571,
            "total_duration": 913,
        }
    ]
}


class FakeBackend:
    """The two methods RouteCache needs, over a dict."""

    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.reads = 0
        self.writes = 0

    async def get(self, key: str):
        self.reads += 1
        return self.store.get(key)

    async def set(self, key: str, value: str, ex: int | None = None):
        self.writes += 1
        self.store[key] = value
        return True


class BrokenBackend:
    """Redis that is down."""

    async def get(self, key: str):
        raise ConnectionError("redis is down")

    async def set(self, key: str, value: str, ex: int | None = None):
        raise ConnectionError("redis is down")


@pytest.fixture
def env(request):
    """A TestClient plus the call counter and cache backend behind it.

    TestClient is built without entering its context manager on purpose, so
    lifespan does not run and nothing tries to reach a real Redis or 2GIS.
    """
    marker = request.node.get_closest_marker("backend")
    backend = marker.kwargs["cls"]() if marker else FakeBackend()
    calls = {"n": 0}

    async def handler(http_request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(200, json=SAMPLE)

    client = AsyncCarRoutingClient(
        key="test-key",
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        max_retries=0,
    )
    cache = RouteCache(backend, ttl_s=600)
    service = RoutingService(client, cache)

    app.dependency_overrides[get_service] = lambda: service
    app.state.cache = cache
    app.state.has_key = True
    try:
        yield TestClient(app), calls, backend
    finally:
        app.dependency_overrides.clear()


# -- single route -----------------------------------------------------------


def test_post_route(env):
    client, calls, _ = env
    response = client.post("/v1/route", json={"origin": A, "destination": B})

    assert response.status_code == 200
    body = response.json()
    assert body["duration_s"] == 913
    assert body["distance_m"] == 3571
    assert body["duration_min"] == 15.2
    assert body["traffic_aware"] is True
    assert body["cached"] is False
    assert calls["n"] == 1


def test_second_identical_call_is_served_from_cache(env):
    client, calls, backend = env
    payload = {"origin": A, "destination": B}

    first = client.post("/v1/route", json=payload).json()
    second = client.post("/v1/route", json=payload).json()

    assert first["cached"] is False
    assert second["cached"] is True
    assert second["duration_s"] == 913
    assert calls["n"] == 1, "cache hit must not reach upstream"
    assert backend.writes == 1


def test_get_route_query_form(env):
    client, _, _ = env
    response = client.get(
        "/v1/route",
        params={"origin": "76.917284,43.239218", "destination": "76.9575,43.244608"},
    )

    assert response.status_code == 200
    assert response.json()["duration_s"] == 913


def test_get_route_rejects_malformed_pair(env):
    client, _, _ = env
    response = client.get(
        "/v1/route", params={"origin": "not-a-point", "destination": "76.9,43.2"}
    )

    assert response.status_code == 422
    assert "lon,lat" in response.json()["detail"]


def test_out_of_range_coordinates_are_rejected(env):
    client, calls, _ = env
    response = client.post(
        "/v1/route", json={"origin": {"lon": 76.9, "lat": 91.0}, "destination": B}
    )

    assert response.status_code == 422
    assert calls["n"] == 0


def test_unknown_field_is_rejected(env):
    client, _, _ = env
    response = client.post(
        "/v1/route", json={"origin": A, "destination": B, "mode": "walking"}
    )

    assert response.status_code == 422


# -- matrix -----------------------------------------------------------------


def test_all_pairs_matrix(env):
    client, calls, _ = env
    response = client.post("/v1/matrix", json={"origins": [A, B, C]})

    assert response.status_code == 200
    body = response.json()
    assert len(body["durations_s"]) == 3
    assert all(len(row) == 3 for row in body["durations_s"])
    for i in range(3):
        assert body["durations_s"][i][i] == 0
        assert body["distances_m"][i][i] == 0
    assert body["durations_s"][0][1] == 913
    assert body["failures"] == []

    meta = body["meta"]
    assert meta["pairs"] == 9
    assert meta["trivial"] == 3
    assert meta["fetched"] + meta["from_cache"] == 6
    assert meta["failed"] == 0
    assert calls["n"] == meta["fetched"]


def test_matrix_reuses_cache_from_an_earlier_route_call(env):
    client, calls, _ = env

    client.post("/v1/route", json={"origin": A, "destination": B})
    assert calls["n"] == 1

    body = client.post("/v1/matrix", json={"origins": [A, B]}).json()

    assert body["meta"]["from_cache"] == 1, "A->B was already cached"
    assert body["meta"]["fetched"] == 1, "only B->A is new"
    assert calls["n"] == 2


def test_rectangular_matrix(env):
    client, _, _ = env
    body = client.post(
        "/v1/matrix", json={"origins": [A], "destinations": [B, C]}
    ).json()

    assert len(body["durations_s"]) == 1
    assert len(body["durations_s"][0]) == 2


def test_matrix_reports_a_failed_pair_without_failing(env):
    client, _, _ = env
    calls = {"n": 0}

    async def one_bad(http_request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(500, text="boom")
        return httpx.Response(200, json=SAMPLE)

    upstream = AsyncCarRoutingClient(
        key="k",
        client=httpx.AsyncClient(transport=httpx.MockTransport(one_bad)),
        max_retries=0,
        max_concurrency=1,
    )
    service = RoutingService(upstream, RouteCache(FakeBackend(), ttl_s=600))
    app.dependency_overrides[get_service] = lambda: service

    body = client.post("/v1/matrix", json={"origins": [A, B]}).json()

    assert len(body["failures"]) == 1
    assert body["meta"]["failed"] == 1
    failed = body["failures"][0]
    assert body["durations_s"][failed["origin"]][failed["destination"]] is None


def test_matrix_size_limits(env):
    client, calls, _ = env
    app.dependency_overrides[get_settings] = lambda: Settings(
        max_points_per_side=3, max_matrix_pairs=4
    )
    try:
        too_wide = client.post("/v1/matrix", json={"origins": [A, B, C, A]})
        assert too_wide.status_code == 422
        assert "per side" in too_wide.json()["detail"]

        too_many = client.post(
            "/v1/matrix", json={"origins": [A, B, C], "destinations": [A, B, C]}
        )
        assert too_many.status_code == 422
        assert "exceeds the limit" in too_many.json()["detail"]
        assert calls["n"] == 0
    finally:
        app.dependency_overrides.pop(get_settings, None)


def test_matrix_needs_origins(env):
    client, _, _ = env
    assert client.post("/v1/matrix", json={"origins": []}).status_code == 422


# -- degradation and errors -------------------------------------------------


@pytest.mark.backend(cls=BrokenBackend)
def test_a_dead_cache_does_not_break_the_api(env):
    client, calls, _ = env
    payload = {"origin": A, "destination": B}

    first = client.post("/v1/route", json=payload)
    second = client.post("/v1/route", json=payload)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["cached"] is False
    assert second.json()["cached"] is False, "no cache means every call is a miss"
    assert calls["n"] == 2


def test_dead_upstream_key_becomes_502_with_an_actionable_message(env):
    client, _, _ = env

    async def forbidden(http_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            403, json={"type": "forbidden", "message": "invalid_request"}
        )

    upstream = AsyncCarRoutingClient(
        key="k",
        client=httpx.AsyncClient(transport=httpx.MockTransport(forbidden)),
        max_retries=0,
    )
    app.dependency_overrides[get_service] = lambda: RoutingService(
        upstream, RouteCache(FakeBackend(), ttl_s=600)
    )

    response = client.post("/v1/route", json={"origin": A, "destination": B})

    assert response.status_code == 502
    assert "rotated" in response.json()["detail"]


def test_no_route_becomes_404(env):
    client, _, _ = env

    async def empty(http_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"result": []})

    upstream = AsyncCarRoutingClient(
        key="k",
        client=httpx.AsyncClient(transport=httpx.MockTransport(empty)),
        max_retries=0,
    )
    app.dependency_overrides[get_service] = lambda: RoutingService(
        upstream, RouteCache(FakeBackend(), ttl_s=600)
    )

    response = client.post("/v1/route", json={"origin": A, "destination": B})
    assert response.status_code == 404


def test_health(env):
    client, _, _ = env
    body = client.get("/health").json()

    assert body["status"] == "ok"
    assert body["cache"] == "ready"
    assert body["upstream_key"] == "configured"


def test_openapi_documents_both_endpoints(env):
    client, _, _ = env
    paths = client.get("/openapi.json").json()["paths"]

    assert "/v1/route" in paths
    assert "/v1/matrix" in paths
