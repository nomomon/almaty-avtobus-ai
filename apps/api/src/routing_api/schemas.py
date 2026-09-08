"""Request and response bodies."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class PointIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lon: float = Field(ge=-180.0, le=180.0, examples=[76.917284])
    lat: float = Field(ge=-90.0, le=90.0, examples=[43.239218])


class RouteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    origin: PointIn
    destination: PointIn


class RouteResponse(BaseModel):
    distance_m: int
    duration_s: int
    distance_km: float
    duration_min: float
    mean_speed_kmh: float | None
    traffic_aware: bool = Field(
        description="Whether 2GIS said it accounted for live traffic."
    )
    cached: bool = Field(description="Served from the Redis cache.")


class MatrixRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    origins: list[PointIn] = Field(min_length=1)
    destinations: list[PointIn] | None = Field(
        default=None,
        description="Omit for an all-pairs matrix over origins.",
    )


class MatrixFailure(BaseModel):
    origin: int
    destination: int
    error: str


class MatrixMeta(BaseModel):
    pairs: int = Field(description="Cells in the matrix, including the diagonal.")
    from_cache: int
    fetched: int
    trivial: int = Field(description="Identical pairs answered as zero, no call.")
    failed: int
    elapsed_ms: int


class MatrixResponse(BaseModel):
    durations_s: list[list[int | None]]
    distances_m: list[list[int | None]]
    failures: list[MatrixFailure]
    meta: MatrixMeta


class HealthResponse(BaseModel):
    status: str
    cache: str = Field(description="'ready', 'disabled', or 'unavailable'.")
    upstream_key: str = Field(description="'configured' or 'missing'.")
