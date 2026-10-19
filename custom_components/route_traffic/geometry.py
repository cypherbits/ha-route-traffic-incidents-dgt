"""Geometry helpers for matching incidents against a route corridor."""

from __future__ import annotations

import math
from collections.abc import Sequence

_METERS_PER_DEG_LAT = 110_574.0
_CELL_DEG = 0.01  # Roughly 1.1 km at mid latitudes.


def meters_per_deg_lon(latitude: float) -> float:
    """Return the length of one degree of longitude in meters."""
    return 111_320.0 * math.cos(math.radians(latitude))


def point_to_segment_m(
    lat: float,
    lon: float,
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    """Return the distance in meters between a point and a line segment.

    A local equirectangular projection is used, which is accurate to well
    below one meter for the distances involved in road matching.
    """
    kx = meters_per_deg_lon((lat1 + lat2) / 2)

    ax, ay = lon1 * kx, lat1 * _METERS_PER_DEG_LAT
    bx, by = lon2 * kx, lat2 * _METERS_PER_DEG_LAT
    px, py = lon * kx, lat * _METERS_PER_DEG_LAT

    dx, dy = bx - ax, by - ay
    seg_sq = dx * dx + dy * dy
    if seg_sq == 0.0:
        return math.hypot(px - ax, py - ay)

    t = ((px - ax) * dx + (py - ay) * dy) / seg_sq
    t = max(0.0, min(1.0, t))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


class RouteGeometry:
    """A route polyline indexed on a coarse grid for fast proximity queries."""

    __slots__ = (
        "coordinates",
        "_grid",
        "_segments",
        "_min_lat",
        "_max_lat",
        "_min_lon",
        "_max_lon",
        "_length_m",
    )

    def __init__(self, coordinates: Sequence[Sequence[float]]) -> None:
        """Initialize from a sequence of ``(longitude, latitude)`` pairs."""
        if len(coordinates) < 2:
            raise ValueError("A route requires at least two coordinates")

        self.coordinates: tuple[tuple[float, float], ...] = tuple(
            (float(lon), float(lat)) for lon, lat in coordinates
        )
        self._segments: tuple[tuple[float, float, float, float], ...] = tuple(
            (lat1, lon1, lat2, lon2)
            for (lon1, lat1), (lon2, lat2) in zip(
                self.coordinates, self.coordinates[1:]
            )
        )

        lats = [lat for _lon, lat in self.coordinates]
        lons = [lon for lon, _lat in self.coordinates]
        self._min_lat, self._max_lat = min(lats), max(lats)
        self._min_lon, self._max_lon = min(lons), max(lons)

        grid: dict[tuple[int, int], list[int]] = {}
        length = 0.0
        for index, (lat1, lon1, lat2, lon2) in enumerate(self._segments):
            length += _segment_length_m(lat1, lon1, lat2, lon2)
            for cell in _cells_for_segment(lat1, lon1, lat2, lon2):
                grid.setdefault(cell, []).append(index)

        self._grid = grid
        self._length_m = length

    @property
    def length_m(self) -> float:
        """Return the route length in meters."""
        return self._length_m

    def distance_to(self, lat: float, lon: float, search_radius_m: float) -> float:
        """Return the distance in meters from a point to the route.

        Only grid cells reachable within ``search_radius_m`` are inspected, so
        the query stays cheap even for very long routes. ``math.inf`` is
        returned when no segment is close enough.
        """
        lat_margin = search_radius_m / _METERS_PER_DEG_LAT
        lon_margin = search_radius_m / meters_per_deg_lon(lat)

        if (
            lat < self._min_lat - lat_margin
            or lat > self._max_lat + lat_margin
            or lon < self._min_lon - lon_margin
            or lon > self._max_lon + lon_margin
        ):
            return math.inf

        cell_radius = max(1, int(math.ceil(search_radius_m / 111_000 / _CELL_DEG)))
        base_x = int(math.floor(lon / _CELL_DEG))
        base_y = int(math.floor(lat / _CELL_DEG))

        best = math.inf
        seen: set[int] = set()
        for dx in range(-cell_radius, cell_radius + 1):
            for dy in range(-cell_radius, cell_radius + 1):
                for index in self._grid.get((base_x + dx, base_y + dy), ()):
                    if index in seen:
                        continue
                    seen.add(index)
                    lat1, lon1, lat2, lon2 = self._segments[index]
                    distance = point_to_segment_m(lat, lon, lat1, lon1, lat2, lon2)
                    if distance < best:
                        best = distance
        return best

    def nearest_distance_m(
        self, points: Sequence[tuple[float, float]], search_radius_m: float
    ) -> float:
        """Return the smallest distance from any of ``points`` to the route."""
        best = math.inf
        for lat, lon in points:
            distance = self.distance_to(lat, lon, search_radius_m)
            if distance < best:
                best = distance
                if best <= search_radius_m / 10:
                    break
        return best


def _segment_length_m(
    lat1: float, lon1: float, lat2: float, lon2: float
) -> float:
    """Return the length of a segment in meters."""
    kx = meters_per_deg_lon((lat1 + lat2) / 2)
    dx = (lon2 - lon1) * kx
    dy = (lat2 - lat1) * _METERS_PER_DEG_LAT
    return math.hypot(dx, dy)


def _cells_for_segment(
    lat1: float, lon1: float, lat2: float, lon2: float
) -> set[tuple[int, int]]:
    """Return every grid cell touched by a segment's bounding box."""
    min_lat, max_lat = sorted((lat1, lat2))
    min_lon, max_lon = sorted((lon1, lon2))
    cells: set[tuple[int, int]] = set()
    for x in range(
        int(math.floor(min_lon / _CELL_DEG)),
        int(math.floor(max_lon / _CELL_DEG)) + 1,
    ):
        for y in range(
            int(math.floor(min_lat / _CELL_DEG)),
            int(math.floor(max_lat / _CELL_DEG)) + 1,
        ):
            cells.add((x, y))
    return cells
