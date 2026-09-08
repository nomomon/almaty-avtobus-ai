"""Settings, read from the environment (and .env)."""

from __future__ import annotations

import os
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # -- upstream ----------------------------------------------------------
    twogis_routing_key: str | None = Field(
        default=None,
        description="2GIS key. Falls back to TWOGIS_API_KEY / 2GIS_API_KEY.",
    )
    twogis_api_key: str | None = None
    upstream_timeout_s: float = Field(default=20.0, gt=0)
    upstream_max_concurrency: int = Field(default=8, ge=1, le=64)
    upstream_max_retries: int = Field(default=2, ge=0, le=5)

    # -- cache -------------------------------------------------------------
    redis_url: str = "redis://localhost:6379/0"
    cache_ttl_s: int = Field(default=600, ge=0, description="0 disables caching.")
    cache_prefix: str = "route:v1"
    #: Decimal places coordinates are rounded to when building a cache key.
    #: 5 is ~1 m (near-exact matches only); 4 is ~11 m and lifts the hit rate
    #: at the cost of answering with a route from slightly next door.
    cache_coord_precision: int = Field(default=5, ge=2, le=7)

    # -- limits ------------------------------------------------------------
    #: Guardrails, because a matrix costs one upstream request per pair.
    max_points_per_side: int = Field(default=25, ge=1)
    max_matrix_pairs: int = Field(default=200, ge=1)

    def resolved_key(self) -> str | None:
        # `2GIS_API_KEY` starts with a digit, so it cannot be a settings field
        # name; read it straight from the environment to stay compatible with
        # the name the old Next.js app used.
        return (
            self.twogis_routing_key
            or self.twogis_api_key
            or os.environ.get("2GIS_API_KEY")
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
