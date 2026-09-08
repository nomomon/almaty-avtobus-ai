#!/usr/bin/env python3
"""Is the configured 2GIS key still alive? One cheap route, one exit code.

    python scripts/check_key.py            # human readable
    python scripts/check_key.py --quiet    # exit code only, for cron

Exit codes:
    0  working
    3  key rejected -- rotated, revoked, or not provisioned (DeadKeyError)
    4  reachable but failing for another reason (quota, outage, bad body)
    5  no key configured

Point cron or CI at this so a rotated key shows up as an alert rather than as
users reporting that routing "just stopped working".
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import UTC, datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from car_routing import (  # noqa: E402
    CarRoutingClient,
    CarRoutingError,
    DeadKeyError,
    load_env,
    resolve_key,
)

# Two points ~3.5 km apart in central Almaty, from the captured session.
A = (76.917284, 43.239218)
B = (76.9575, 43.244608)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--key", default=None)
    parser.add_argument("--env-file", default=".env")
    parser.add_argument(
        "--quiet", action="store_true", help="print nothing, just set the exit code"
    )
    args = parser.parse_args()

    def say(message: str) -> None:
        if not args.quiet:
            print(message)

    load_env(args.env_file)
    stamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%SZ")

    try:
        key = resolve_key(args.key)
    except CarRoutingError as exc:
        say(f"[{stamp}] NO KEY: {exc}")
        return 5

    try:
        with CarRoutingClient(key=key, max_retries=1) as client:
            route = client.route(A, B)
    except DeadKeyError as exc:
        say(
            f"[{stamp}] DEAD KEY (...{key[-6:]}): {exc}\n"
            "  If this key worked before and nothing changed on your side, it was\n"
            "  rotated. Replace it in your .env; better, issue your own at\n"
            "  dev.2gis.com so this stops being a recurring chore."
        )
        return 3
    except CarRoutingError as exc:
        say(f"[{stamp}] FAILING (...{key[-6:]}): {exc}")
        return 4

    say(
        f"[{stamp}] OK (...{key[-6:]}): {route} "
        f"at {route.mean_speed_kmh} km/h, traffic_aware={route.traffic_aware}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
