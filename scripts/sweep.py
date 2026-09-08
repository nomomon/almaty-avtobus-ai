#!/usr/bin/env python3
"""Live checks against 2GIS. Run from a machine with network access.

    python scripts/sweep.py routes    # exercise our carrouting client end to end
    python scripts/sweep.py matrix    # probe the official Distance Matrix API
    python scripts/sweep.py both

Key resolution is the same as the client's: --key, else TWOGIS_ROUTING_KEY /
TWOGIS_API_KEY / 2GIS_API_KEY.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from car_routing import CarRoutingClient, CarRoutingError, resolve_key  # noqa: E402

# (name, lon, lat) -- Almaty landmarks, coordinates approximate except the
# first two, which come from the captured browser session.
PLACES = [
    ("Kazakhstan Hotel", 76.9575, 43.244608),
    ("Capture point A", 76.917284, 43.239218),
    ("Sairan bus station", 76.8895, 43.2385),
    ("Almaty-2 station", 76.9296, 43.2748),
    ("Dostyk Plaza", 76.9564, 43.2337),
    ("Airport", 77.0119, 43.3521),
]


def sweep_routes(key: str, workers: int) -> int:
    points = [(lon, lat) for _, lon, lat in PLACES]
    names = [name for name, _, _ in PLACES]
    n = len(points)

    print(f"== carrouting sweep: {n}x{n} = {n * (n - 1)} live requests\n")
    started = time.monotonic()
    with CarRoutingClient(key=key, max_workers=workers) as client:
        try:
            matrix = client.matrix(points)
        except CarRoutingError as exc:
            print(f"FAILED outright: {exc}")
            return 1
    elapsed = time.monotonic() - started

    print(matrix.format_table("duration_min"))
    print()
    print(matrix.format_table("distance_km"))
    print()
    for i, name in enumerate(names):
        print(f"  {i} = {name}")
    print()

    good = [c for row in matrix.cells for c in row if c.ok and c.duration_s]
    bad = matrix.failures
    print(f"{len(good)} routed, {len(bad)} failed, {elapsed:.1f}s wall clock")
    if good:
        speeds = sorted(
            c.distance_m / c.duration_s * 3.6 for c in good if c.duration_s
        )
        print(
            f"mean speed: min {speeds[0]:.1f} / median "
            f"{speeds[len(speeds) // 2]:.1f} / max {speeds[-1]:.1f} km/h"
        )
        # Sanity: city driving should land roughly in 5..80 km/h. Anything
        # outside that means we are misreading a unit somewhere.
        odd = [s for s in speeds if not 5 <= s <= 80]
        print(
            f"implausible speeds: {len(odd)}"
            + (f" -> {[round(s, 1) for s in odd]}" if odd else " (units look right)")
        )
        asym = [
            (i, j)
            for i in range(len(points))
            for j in range(i + 1, len(points))
            if matrix.cell(i, j).duration_s
            and matrix.cell(j, i).duration_s
            and abs(matrix.cell(i, j).duration_s - matrix.cell(j, i).duration_s)
            > 0.5 * matrix.cell(i, j).duration_s
        ]
        print(f"strongly asymmetric pairs (expected, one-way streets + jams): {len(asym)}")

    for cell in bad:
        print(f"  FAIL {cell.origin}->{cell.destination}: {cell.error}")
    return 0 if not bad else 2


# -- official Distance Matrix API -------------------------------------------
#
# 2GIS sells this as the Distance Matrix API. The shape below is my best
# recollection of it, NOT something confirmed against a live response, so treat
# every variant as a guess and read the printed status codes rather than
# trusting the labels. A 403 here most likely means "key not provisioned for
# this product" rather than "wrong body".

MATRIX_URL = "https://routing.api.2gis.com/get_dist_matrix"

VARIANTS: list[tuple[str, dict, dict]] = [
    (
        "v2.0 sources/targets, driving",
        {"version": "2.0"},
        {
            "points": [{"lat": lat, "lon": lon} for _, lon, lat in PLACES[:3]],
            "sources": [0],
            "targets": [1, 2],
            "mode": "driving",
        },
    ),
    (
        "v2.0 sources/targets, jam traffic",
        {"version": "2.0"},
        {
            "points": [{"lat": lat, "lon": lon} for _, lon, lat in PLACES[:3]],
            "sources": [0],
            "targets": [1, 2],
            "mode": "driving",
            "traffic_mode": "jam",
        },
    ),
    (
        "v2.0 all pairs (no sources/targets)",
        {"version": "2.0"},
        {"points": [{"lat": lat, "lon": lon} for _, lon, lat in PLACES[:3]]},
    ),
    (
        "v1.0",
        {"version": "1.0"},
        {
            "points": [{"lat": lat, "lon": lon} for _, lon, lat in PLACES[:3]],
            "sources": [0],
            "targets": [1, 2],
        },
    ),
]


def probe_matrix(key: str) -> int:
    print("== Distance Matrix API probe\n")
    reachable = False
    with httpx.Client(timeout=30.0) as client:
        for label, params, body in VARIANTS:
            try:
                response = client.post(
                    MATRIX_URL, params={"key": key, **params}, json=body
                )
            except httpx.HTTPError as exc:
                print(f"  {label:<42} transport error: {exc}")
                continue

            snippet = response.text[:220].replace("\n", " ")
            print(f"  {label:<42} HTTP {response.status_code}  {snippet}")
            if response.status_code == 200:
                reachable = True
                try:
                    print(
                        "    parsed: "
                        + json.dumps(response.json(), ensure_ascii=False)[:600]
                    )
                except ValueError:
                    pass

    print()
    if reachable:
        print("At least one variant worked -- paste the parsed output and the")
        print("client can switch to one request per matrix instead of n*m.")
    else:
        print("Nothing worked. Most likely this key is not provisioned for the")
        print("Distance Matrix product. Check which APIs your key covers in the")
        print("dev.2gis.com dashboard, and see the README notes on finding it.")
    return 0 if reachable else 3


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("what", choices=["routes", "matrix", "both"])
    parser.add_argument("--key", default=None)
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args()

    try:
        key = resolve_key(args.key)
    except CarRoutingError as exc:
        print(exc)
        return 1
    print(f"key: ...{key[-6:]}\n")

    codes = []
    if args.what in ("routes", "both"):
        codes.append(sweep_routes(key, args.workers))
        print()
    if args.what in ("matrix", "both"):
        codes.append(probe_matrix(key))
    return max(codes)


if __name__ == "__main__":
    sys.exit(main())
