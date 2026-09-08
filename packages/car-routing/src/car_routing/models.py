"""Pydantic models for the 2GIS car routing client."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

PointLike = "Point | tuple[float, float] | list[float] | dict[str, Any]"


class Point(BaseModel):
    """A geographic point.

    2GIS speaks ``x`` = longitude, ``y`` = latitude, so tuples and lists are
    read as ``(lon, lat)`` to match. Use :meth:`from_latlon` if your data is
    the other way round.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    lon: float = Field(ge=-180.0, le=180.0, description="Longitude (2GIS 'x').")
    lat: float = Field(ge=-90.0, le=90.0, description="Latitude (2GIS 'y').")
    name: str = Field(default="point", max_length=200)

    @classmethod
    def from_latlon(cls, lat: float, lon: float, name: str = "point") -> Point:
        return cls(lon=lon, lat=lat, name=name)

    @classmethod
    def coerce(cls, value: Any) -> Point:
        """Accept a ``Point``, a ``(lon, lat)`` pair, or a mapping."""
        if isinstance(value, Point):
            return value
        if isinstance(value, (tuple, list)):
            if len(value) != 2:
                raise ValueError(
                    f"expected a (lon, lat) pair, got {len(value)} values: {value!r}"
                )
            return cls(lon=float(value[0]), lat=float(value[1]))
        if isinstance(value, dict):
            return cls.model_validate(value)
        raise TypeError(f"cannot read a point from {type(value).__name__}: {value!r}")

    @classmethod
    def coerce_all(cls, values: Iterable[Any]) -> list[Point]:
        return [cls.coerce(v) for v in values]


class Route(BaseModel):
    """One route alternative, reduced to what we actually need."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    distance_m: int = Field(ge=0, description="Total distance in metres.")
    duration_s: int = Field(ge=0, description="Total travel time in seconds.")
    algorithm: str | None = Field(
        default=None,
        description="Server label, e.g. 'с учётом пробок' (traffic-aware).",
    )
    route_id: str | None = None

    @property
    def distance_km(self) -> float:
        return round(self.distance_m / 1000.0, 2)

    @property
    def duration_min(self) -> float:
        return round(self.duration_s / 60.0, 1)

    @property
    def mean_speed_kmh(self) -> float | None:
        if self.duration_s == 0:
            return None
        return round(self.distance_m / self.duration_s * 3.6, 1)

    @property
    def traffic_aware(self) -> bool:
        """Whether the server said it accounted for jams."""
        return bool(self.algorithm and "пробок" in self.algorithm)

    def __str__(self) -> str:
        return f"{self.duration_min} min / {self.distance_km} km"


class MatrixCell(BaseModel):
    """One origin-destination pair. ``error`` is set instead of the values
    when that single pair failed; the rest of the matrix still comes back."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    origin: int = Field(ge=0, description="Index into DistanceMatrix.origins.")
    destination: int = Field(ge=0, description="Index into .destinations.")
    distance_m: int | None = Field(default=None, ge=0)
    duration_s: int | None = Field(default=None, ge=0)
    error: str | None = None

    @model_validator(mode="after")
    def _either_values_or_error(self) -> MatrixCell:
        has_values = self.distance_m is not None and self.duration_s is not None
        if has_values == (self.error is not None):
            raise ValueError(
                "a cell needs either both distance_m and duration_s, or an error"
            )
        return self

    @property
    def ok(self) -> bool:
        return self.error is None

    @property
    def duration_min(self) -> float | None:
        return None if self.duration_s is None else round(self.duration_s / 60.0, 1)

    @property
    def distance_km(self) -> float | None:
        return None if self.distance_m is None else round(self.distance_m / 1000.0, 2)


class DistanceMatrix(BaseModel):
    """Time and distance for every origin-destination pair.

    ``cells[i][j]`` is origins[i] -> destinations[j].
    """

    model_config = ConfigDict(extra="forbid")

    origins: list[Point] = Field(min_length=1)
    destinations: list[Point] = Field(min_length=1)
    cells: list[list[MatrixCell]]

    @field_validator("cells")
    @classmethod
    def _rectangular(cls, cells: list[list[MatrixCell]]) -> list[list[MatrixCell]]:
        widths = {len(row) for row in cells}
        if len(widths) > 1:
            raise ValueError(f"ragged matrix, row widths {sorted(widths)}")
        return cells

    @model_validator(mode="after")
    def _shape_matches_points(self) -> DistanceMatrix:
        want = (len(self.origins), len(self.destinations))
        got = (len(self.cells), len(self.cells[0]) if self.cells else 0)
        if want != got:
            raise ValueError(f"matrix is {got}, expected {want} from the point lists")
        for i, row in enumerate(self.cells):
            for j, cell in enumerate(row):
                if (cell.origin, cell.destination) != (i, j):
                    raise ValueError(
                        f"cell at [{i}][{j}] is indexed "
                        f"({cell.origin}, {cell.destination})"
                    )
        return self

    def cell(self, origin: int, destination: int) -> MatrixCell:
        return self.cells[origin][destination]

    @property
    def durations_s(self) -> list[list[int | None]]:
        return [[c.duration_s for c in row] for row in self.cells]

    @property
    def durations_min(self) -> list[list[float | None]]:
        return [[c.duration_min for c in row] for row in self.cells]

    @property
    def distances_m(self) -> list[list[int | None]]:
        return [[c.distance_m for c in row] for row in self.cells]

    @property
    def distances_km(self) -> list[list[float | None]]:
        return [[c.distance_km for c in row] for row in self.cells]

    @property
    def failures(self) -> list[MatrixCell]:
        return [c for row in self.cells for c in row if not c.ok]

    def to_records(self) -> list[dict[str, Any]]:
        """Flat rows, handy for pandas or CSV."""
        return [
            {
                "origin": i,
                "destination": j,
                "origin_lon": self.origins[i].lon,
                "origin_lat": self.origins[i].lat,
                "destination_lon": self.destinations[j].lon,
                "destination_lat": self.destinations[j].lat,
                "duration_s": cell.duration_s,
                "distance_m": cell.distance_m,
                "error": cell.error,
            }
            for i, row in enumerate(self.cells)
            for j, cell in enumerate(row)
        ]

    def format_table(self, value: str = "duration_min") -> str:
        """Render one metric as a fixed-width grid, for eyeballing results."""
        grids: dict[str, Sequence[Sequence[Any]]] = {
            "duration_min": self.durations_min,
            "duration_s": self.durations_s,
            "distance_km": self.distances_km,
            "distance_m": self.distances_m,
        }
        if value not in grids:
            raise ValueError(f"unknown metric {value!r}, pick one of {list(grids)}")
        grid = grids[value]
        header = "      " + "".join(f"{j:>10}" for j in range(len(self.destinations)))
        rows = [
            f"{i:>4}  " + "".join(f"{'-' if v is None else v:>10}" for v in grid[i])
            for i in range(len(self.origins))
        ]
        return "\n".join([f"{value} (origins x destinations)", header, *rows])
