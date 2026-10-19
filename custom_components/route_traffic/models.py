"""Data models shared across routing providers and incident providers."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True, slots=True)
class Route:
    """A resolved route between two points."""

    coordinates: tuple[tuple[float, float], ...]
    distance_m: float
    duration_s: float
    provider: str

    @property
    def distance_km(self) -> float:
        """Return the route distance in kilometers."""
        return round(self.distance_m / 1000, 2)

    @property
    def duration_min(self) -> float:
        """Return the estimated driving time in minutes."""
        return round(self.duration_s / 60, 1)


@dataclass(frozen=True, slots=True)
class Incident:
    """A traffic incident reported by a provider."""

    uid: str
    provider: str
    road: str
    severity: str
    cause: str
    is_closure: bool
    municipality: str
    started_at: datetime | None
    points: tuple[tuple[float, float], ...]
    management: str = ""
    detail: str = ""
    distance_m: float = field(default=float("inf"))

    @property
    def matched(self) -> bool:
        """Return True when the incident falls inside the route corridor."""
        return self.distance_m != float("inf")

    def as_dict(self) -> dict[str, object]:
        """Return a serializable representation for entity attributes."""
        return {
            "id": self.uid,
            "provider": self.provider,
            "road": self.road,
            "severity": self.severity,
            "cause": self.cause,
            "detail": self.detail,
            "management": self.management,
            "is_closure": self.is_closure,
            "municipality": self.municipality,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "distance_from_route_m": (
                round(self.distance_m) if self.matched else None
            ),
            "latitude": round(self.points[0][0], 6) if self.points else None,
            "longitude": round(self.points[0][1], 6) if self.points else None,
        }
