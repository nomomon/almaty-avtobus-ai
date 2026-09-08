"""Cache tests against a real Redis when one is reachable, else skipped.

REDIS_TEST_URL points these at a server; they are skipped when it is absent or
unreachable, so the suite stays green on machines without Redis.
"""

from __future__ import annotations

import os
import uuid

import pytest
from car_routing import Point, Route
from routing_api.cache import RouteCache, make_backend

REDIS_URL = os.environ.get("REDIS_TEST_URL")

A = Point(lon=76.917284, lat=43.239218)
B = Point(lon=76.9575, lat=43.244608)
ROUTE = Route(distance_m=3571, duration_s=913, algorithm="с учётом пробок")


@pytest.fixture
async def cache():
    if not REDIS_URL:
        pytest.skip("REDIS_TEST_URL is not set")
    backend = await make_backend(REDIS_URL)
    if backend is None:
        pytest.skip(f"cannot reach Redis at {REDIS_URL}")

    # Unique prefix per test run, so nothing collides with real data.
    yield RouteCache(backend, ttl_s=600, prefix=f"test:{uuid.uuid4().hex[:8]}")
    await backend.aclose()


async def test_round_trip(cache):
    assert await cache.get(A, B) is None

    await cache.set(A, B, ROUTE)
    hit = await cache.get(A, B)

    assert hit is not None
    assert (hit.distance_m, hit.duration_s) == (3571, 913)
    assert hit.algorithm == "с учётом пробок"  # survives a JSON round trip


async def test_direction_matters(cache):
    await cache.set(A, B, ROUTE)

    assert await cache.get(A, B) is not None
    assert await cache.get(B, A) is None, "reverse direction is a different key"


async def test_ttl_is_applied(cache):
    await cache.set(A, B, ROUTE)
    ttl = await cache.backend.ttl(cache.key_for(A, B))

    assert 0 < ttl <= 600


async def test_zero_ttl_disables_writes(cache):
    cache.ttl_s = 0
    await cache.set(A, B, ROUTE)

    assert cache.enabled is False
    assert await cache.get(A, B) is None


async def test_coordinate_precision_controls_key_sharing(cache):
    nearby = Point(lon=A.lon + 0.0001, lat=A.lat)  # ~8 m away

    cache.coord_precision = 3
    assert cache.key_for(A, B) == cache.key_for(nearby, B), "3 dp (~100 m) shares a key"

    cache.coord_precision = 7
    assert cache.key_for(A, B) != cache.key_for(nearby, B), "7 dp separates them"


async def test_poisoned_entry_is_treated_as_a_miss(cache):
    await cache.backend.set(cache.key_for(A, B), "not json at all")

    assert await cache.get(A, B) is None


async def test_make_backend_returns_none_for_a_dead_server():
    assert (
        await make_backend(
            "redis://127.0.0.1:6",
        )
        is None
    )
