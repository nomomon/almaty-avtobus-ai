"""Tests for the async client. Network stubbed via httpx.MockTransport."""

from __future__ import annotations

import asyncio

import httpx
import pytest
from car_routing import AsyncCarRoutingClient, CarRoutingError, DeadKeyError

A = (76.917284, 43.239218)
B = (76.9575, 43.244608)
C = (76.8895, 43.2385)

SAMPLE = {
    "result": [
        {
            "algorithm": "с учётом пробок",
            "total_distance": 3571,
            "total_duration": 913,
        },
        {"total_distance": 3752, "total_duration": 1019},
    ]
}


def make_client(handler, **kwargs) -> AsyncCarRoutingClient:
    return AsyncCarRoutingClient(
        key="test-key",
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        max_retries=kwargs.pop("max_retries", 0),
        **kwargs,
    )


async def ok(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, json=SAMPLE)


async def test_route_parses_totals():
    async with make_client(ok) as client:
        route = await client.route(A, B)

    assert (route.distance_m, route.duration_s) == (3571, 913)
    assert route.duration_min == 15.2
    assert route.traffic_aware is True


async def test_alternatives_sorted_fastest_first():
    async with make_client(ok) as client:
        routes = await client.alternatives(A, B)

    assert [r.duration_s for r in routes] == [913, 1019]


async def test_matrix_shape_and_zero_diagonal():
    async with make_client(ok) as client:
        matrix = await client.matrix([A, B, C])

    assert (len(matrix.origins), len(matrix.destinations)) == (3, 3)
    for i in range(3):
        assert matrix.cell(i, i).duration_s == 0
    assert matrix.durations_s[0][1] == 913
    assert matrix.failures == []


async def test_rectangular_matrix():
    async with make_client(ok) as client:
        matrix = await client.matrix([A, B], [B, C, A])

    assert (len(matrix.cells), len(matrix.cells[0])) == (2, 3)
    assert matrix.cell(0, 2).duration_s == 0  # A -> A
    assert matrix.cell(0, 0).duration_s == 913  # A -> B


async def test_one_bad_pair_does_not_sink_the_matrix():
    calls = {"n": 0}

    async def flaky(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(400, json={"message": "nope"})
        return httpx.Response(200, json=SAMPLE)

    async with make_client(flaky, max_concurrency=1) as client:
        matrix = await client.matrix([A, B])

    assert len(matrix.failures) == 1
    assert "400" in matrix.failures[0].error


async def test_concurrency_is_bounded():
    live = {"now": 0, "peak": 0}

    async def slow(request: httpx.Request) -> httpx.Response:
        live["now"] += 1
        live["peak"] = max(live["peak"], live["now"])
        await asyncio.sleep(0.02)
        live["now"] -= 1
        return httpx.Response(200, json=SAMPLE)

    async with make_client(slow, max_concurrency=2) as client:
        await client.matrix([A, B, C])  # 6 pairs

    assert live["peak"] <= 2, f"opened {live['peak']} concurrent requests"


async def test_403_is_a_dead_key():
    async def forbidden(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            403, json={"type": "forbidden", "message": "invalid_request"}
        )

    async with make_client(forbidden) as client:
        with pytest.raises(DeadKeyError) as caught:
            await client.route(A, B)

    assert caught.value.status == 403


async def test_retry_then_success():
    calls = {"n": 0}

    async def rate_limited(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] < 2:
            return httpx.Response(429, text="slow down")
        return httpx.Response(200, json=SAMPLE)

    async with make_client(rate_limited, max_retries=2) as client:
        route = await client.route(A, B)

    assert calls["n"] == 2
    assert route.duration_s == 913


async def test_empty_result_is_an_error():
    async def empty(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"result": []})

    async with make_client(empty) as client:
        with pytest.raises(CarRoutingError, match="No route"):
            await client.route(A, B)
