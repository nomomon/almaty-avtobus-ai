#!/usr/bin/env python3
"""Capture a real ctx/2.0 response so the transit models can stop guessing.

    python scripts/dump_transit.py                 # transit + walking
    python scripts/dump_transit.py --mode walk
    python scripts/dump_transit.py --out /tmp

Writes the raw JSON to a file and prints a structural summary: top-level shape,
the keys on one route, and which of the fields the parser looks for actually
exist. Paste that summary (or the file) and the lenient models in
``car_routing.transit`` can become strict.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(
    0, str(Path(__file__).resolve().parents[1] / "packages/car-routing/src")
)

from car_routing import CarRoutingError, Point, load_env  # noqa: E402
from car_routing.transit import (  # noqa: E402
    ALMATY_TRANSPORT,
    PEDESTRIAN,
    TransitClient,
    build_transit_body,
    parse_transit,
)

A = Point(lon=76.85829, lat=43.24486, name="Source")  # Sairan, from the capture
B = Point(lon=76.917284, lat=43.239219, name="Target")


def summarise(payload: object, label: str) -> None:
    print(f"\n--- {label}: structure")
    if isinstance(payload, dict):
        print(f"  top level: dict, keys = {sorted(payload)[:20]}")
        candidates = [k for k in ("result", "routes", "items", "data") if k in payload]
        print(f"  list-bearing keys: {candidates}")
        items = next(
            (payload[k] for k in candidates if isinstance(payload.get(k), list)), []
        )
    elif isinstance(payload, list):
        print(f"  top level: list of {len(payload)}")
        items = payload
    else:
        print(f"  top level: {type(payload).__name__}")
        return

    if not items:
        print("  no route objects found")
        return

    first = items[0]
    if isinstance(first, dict):
        print(f"  route[0] keys = {sorted(first)}")
        wanted = [
            "total_duration",
            "total_distance",
            "total_walkway_distance",
            "transfer_count",
            "crossing_count",
            "movements",
            "routes",
            "legs",
        ]
        print(f"  present of interest: {[k for k in wanted if k in first]}")
        print(f"  missing of interest: {[k for k in wanted if k not in first]}")


def run(client: TransitClient, mode: str, out_dir: Path) -> int:
    transport = PEDESTRIAN if mode == "walk" else ALMATY_TRANSPORT
    body = build_transit_body(A, B, transport=transport)

    print(f"== {mode}: POST {client.url}")
    print(f"   transport = {list(transport)}")
    try:
        payload = client._post(body)
    except CarRoutingError as exc:
        print(f"   FAILED: {exc}")
        return 1

    path = out_dir / f"ctx2_{mode}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"   saved {path} ({path.stat().st_size} bytes)")

    summarise(payload, mode)

    try:
        routes = parse_transit(payload)
    except CarRoutingError as exc:
        print(f"   lenient parser found nothing usable: {exc}")
        return 2

    print(f"\n--- {mode}: what the current parser makes of it")
    for i, route in enumerate(routes[:5]):
        print(f"  [{i}] {route}  route_ids={route.route_ids[:8]}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["transit", "walk", "both"], default="both")
    parser.add_argument("--city", default="almaty")
    parser.add_argument("--key", default=None)
    parser.add_argument("--out", default=".", type=Path)
    args = parser.parse_args()

    load_env()
    args.out.mkdir(parents=True, exist_ok=True)

    modes = ["transit", "walk"] if args.mode == "both" else [args.mode]
    codes = []
    with TransitClient(args.key, city=args.city, max_retries=1) as client:
        for mode in modes:
            codes.append(run(client, mode, args.out))
    return max(codes)


if __name__ == "__main__":
    sys.exit(main())
