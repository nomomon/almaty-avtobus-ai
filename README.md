# almaty-routing

Travel **time** and **distance** in Almaty (and anywhere else 2GIS covers),
with live traffic: by car, on foot, or by public transport. Point to point, or
a full matrix of points. Served as an HTTP API, or used as a library.

Pydantic v2 models throughout, so bad coordinates fail at the boundary instead
of turning into a confusing 403 later.

```
packages/car-routing/   the 2GIS client (car, walking, transit)
apps/api/               FastAPI service + Dockerfile
scripts/                live probes and operational checks
```

```bash
uv sync
uv run pytest -q
```

## Run the API

```bash
docker compose up --build          # api on :8000, redis alongside
# or without docker:
uv run uvicorn routing_api.main:app --reload
```

```bash
curl "localhost:8000/v1/route?origin=76.917284,43.239218&destination=76.9575,43.244608"

curl -X POST localhost:8000/v1/matrix -H 'content-type: application/json' \
  -d '{"origins":[{"lon":76.917284,"lat":43.239218},{"lon":76.9575,"lat":43.244608}]}'

curl localhost:8000/health
```

Interactive docs at `/docs`.

The Redis cache is keyed per **origin-destination pair**, not per request, so a
matrix reuses pairs cached by earlier calls and by overlapping matrices.
Responses report `from_cache` / `fetched` / `trivial`. Default TTL is 600s
(`CACHE_TTL_S`). If Redis is unreachable every lookup degrades to a miss and
the API keeps answering -- a cache outage is not an API outage.

Matrix size is capped (`MAX_POINTS_PER_SIDE`, `MAX_MATRIX_PAIRS`) because each
uncached pair costs one upstream request.

## Deploying

`docker-compose.yml` deliberately **does not publish a host port**. It only
`expose`s 8000, so a reverse proxy reaches the container over the compose
network. Publishing a fixed host port is what causes:

```
Bind for 0.0.0.0:8000 failed: port is already allocated
```

on a box that already runs something on 8000.

For **local** work, `docker-compose.override.yml` publishes the port and is
loaded automatically by a bare `docker compose up`. A deploy that names its
file explicitly (`-f docker-compose.yml`, which is what Dokploy runs) ignores
the override, so it cannot collide on the server.

On **Dokploy**: point the domain at service `api`, container port **8000**, and
set `TWOGIS_ROUTING_KEY` in the environment editor. If Traefik still cannot
reach the container, the app needs to join Dokploy's proxy network -- add it as
an external network on the `api` service.

Need a published port locally on something other than 8000:

```bash
API_PORT=8010 docker compose up
```

## Use as a library


```python
from car_routing import CarRoutingClient

with CarRoutingClient() as client:
    route = client.route((76.917284, 43.239218), (76.9575, 43.244608))

    print(route)  # 15.2 min / 3.57 km
    print(route.duration_s)  # 913
    print(route.distance_m)  # 3571
    print(route.mean_speed_kmh)  # 14.1
    print(route.traffic_aware)  # True
```

Coordinates are **`(lon, lat)`**, matching 2GIS's own `x`/`y`. If your data is
the other way round, use `Point.from_latlon(lat, lon)` — and note the models
will usually catch a silent swap, since a latitude above 90 is rejected.

### Matrix

```python
stops = [
    (76.917284, 43.239218),
    (76.9575, 43.244608),
    (76.8895, 43.2385),
]

with CarRoutingClient() as client:
    m = client.matrix(stops)  # all pairs
    # m = client.matrix(depots, stops)    # or rectangular

print(m.durations_min)  # [[0.0, 15.2, 21.4], [14.8, 0.0, 26.1], ...]
print(m.distances_km)
print(m.format_table("duration_min"))
print(m.to_records())  # flat rows -> pandas.DataFrame(...)
```

`cells[i][j]` is `origins[i] -> destinations[j]`. Identical pairs are zeroed
without a request. A pair whose own request fails gets `error` set on its cell
and shows up in `m.failures`, so one bad pair doesn't lose the other 99.

**Cost**: the endpoint has no batch mode, so an n×m matrix is n×m HTTP
requests, run `max_workers` at a time (default 8). A 20×20 matrix is 380
requests — keep `max_workers` modest and expect to be rate-limited above that.

### Alternatives

```python
for r in client.alternatives(a, b):  # fastest first
    print(r.duration_min, r.distance_km)
```

### Walking and public transport

```python
from car_routing import TransitClient

with TransitClient(city="almaty") as client:
    for route in client.transit(a, b):        # buses, trams, metro
        print(route, route.route_ids)
    print(client.walk(a, b)[0])               # walking only

    # depart at a specific time (unix seconds)
    client.transit(a, b, start_time=1788880355)
```

`AsyncTransitClient` is the same thing awaitable. These wrap
`POST routing.api.2gis.com/ctx/2.0/{city}`, the endpoint behind the transit and
pedestrian tabs on 2gis.kz.

**Caveat**: the request shape is verbatim from a captured session, but the
**response schema is unconfirmed** — the capture had no response bodies. So
`TransitRoute` is lenient: it lifts fields that look right if they're present
and always keeps the untouched payload on `.raw`. Nothing is dropped, but don't
trust a `None`. To fix that:

```bash
python scripts/dump_transit.py     # saves a real response + prints its structure
```

Then the models can become strict and the API can grow `/v1/walk` and
`/v1/transit`. Those endpoints are deliberately absent until then.

## Keys

`CarRoutingClient()` takes `key=...`, otherwise it reads the first of
`TWOGIS_ROUTING_KEY`, `TWOGIS_API_KEY`, `2GIS_API_KEY`. No key is bundled.

Get one at [dev.2gis.com](https://dev.2gis.com): register, create a project,
request a key for the **Directions API** (the productized name for the
`carrouting` endpoint this wraps). They issue a demo key first and then move
you to commercial terms; check the current trial length and pricing there. The
same key also covers the Public Transport API.

A key rejected by 2GIS raises `DeadKeyError`. Worth knowing: 2GIS answers HTTP
403 `{"type": "forbidden", "message": "invalid_request"}` for both a dead key
*and* a malformed body, so `DeadKeyError` covers both cases and says so. If
calls worked yesterday and 403 today with nothing changed on your side, the key
is gone — issue a new one.

Don't run this on the public key that 2gis.kz ships with its own front end. It
works, but it can be rotated without notice, its quota is shared with all of
2gis.kz's traffic, and using it from your own product is outside 2GIS's terms.

That key is app-level configuration, not a session credential: a captured
browser session shows it reported to telemetry as `"apikey"` alongside
`"appVersion"`, distinct from the per-user `user` and `sessionId` fields; shared
across the routing, catalog and advisor APIs; accompanied by a second key used
only for map tiles; and with no `Authorization` header or cookie anywhere in the
session. So it has no expiry to plan around — it simply lives until 2GIS rotates
it, with no notice. Hence `DeadKeyError` and env-supplied keys rather than
anything baked in here.

## What it reads

The response is large (~28 KB per route: geometry, manoeuvres, per-segment
congestion colours, 3D extrusion lines). This client keeps only
`total_distance` and `total_duration`, plus the server's `algorithm` label so
you can confirm traffic was applied — `с учётом пробок` means it was.

Endpoint: `POST https://routing.api.2gis.com/carrouting/6.0.0/global`, with
`type: "online5"` for live traffic. This is the undocumented version the web
app uses; the documented equivalent is `routing/7.0.0/global` with
`traffic_mode: "jam"`. Field names differ, the numbers don't.

### Keeping a key in .env

```bash
cp .env.example .env      # .env is gitignored
$EDITOR .env
```

Anything in `.env` is picked up automatically by the scripts, or explicitly in
your own code:

```python
from car_routing import CarRoutingClient, load_env

load_env()  # no-op if there is no .env
client = CarRoutingClient()
```

A real shell export beats the file, so `TWOGIS_ROUTING_KEY=... python foo.py`
still wins; pass `override=True` if you want the file to take precedence.

### Detecting rotation

Running on a key you don't own works and is slow to break — 2gis.kz's key has
been observed alive across at least three months — but when it does break you
get no notice, and the failure looks like a generic 403. Make it loud:

```bash
python scripts/check_key.py          # 0 working, 3 key dead, 4 other, 5 unset
python scripts/check_key.py --quiet  # for cron
```

One cheap route, one exit code. Wire it into cron or CI daily and a rotated key
shows up as an alert you can act on, rather than as users reporting that
routing quietly stopped working. Exit 3 is the "go paste a fresh value into
`.env`" signal.

For anything user-facing, that chore is the argument for your own key: the
shared quota also means you can be throttled by 2gis.kz's traffic rather than
your own, with no way to tell the two apart from the outside.

## The official Distance Matrix API

2GIS does sell a real matrix product — **Distance Matrix API**, at
`POST https://routing.api.2gis.com/get_dist_matrix?key=...&version=2.0`. One
request returns every source→target pair, which would replace this client's
n×m fan-out entirely. There's also an async variant for large matrices, where
you create a task and poll for the result.

I have **not** confirmed its request or response shape against a live call, and
a key provisioned for Directions is not automatically provisioned for Distance
Matrix — it's a separate product line. So probe it rather than trusting me:

```bash
python scripts/sweep.py matrix        # tries several body shapes, prints statuses
```

A 403 there almost certainly means "key not enabled for this product", not
"wrong body".

### Finding it for real

1. **Your dashboard** — dev.2gis.com → your project → the key's page lists
   exactly which APIs it covers. This answers "does my key support it" in one
   look, and is the fastest path.
2. **The docs** — docs.2gis.com, under the navigation/routing APIs. The
   Distance Matrix page carries the authoritative request schema, the
   sources/targets semantics, and the per-request point limit (matrix products
   normally cap total points hard).
3. **Ask sales/support** — matrix APIs are usually quoted per-request rather
   than bundled into a self-serve tier, so if the dashboard doesn't show it,
   enabling it is a conversation, not a checkbox.

If a variant in `scripts/sweep.py` comes back 200, paste the output and the
client can grow a `matrix()` fast path that costs one request instead of n×m.

## Tests

```bash
pip install pytest
python -m pytest tests -q
```

18 offline tests (network stubbed via `httpx.MockTransport`) covering
validation, matrix assembly, partial failure, retries and key resolution. One
live smoke test runs only when a key is in the environment.

Verified against a real response on 2026-09-08: Kazakhstan Hotel → Almaty
point, 3571 m / 913 s, matching the `"15 мин"` the API returns for its own UI.

One caveat on the request body: the web app sends an `object_id` per point (a
catalog POI id it has because the user clicked a POI). Arbitrary coordinates
have none, so it's omitted — the only part of the request not confirmed against
a live 200. If you see `invalid_request`, suspect that first.
