"""Routing providers."""

from __future__ import annotations

from .base import RoutingError, RoutingProvider
from .osrm import OsrmRoutingProvider
from .waze import WazeRoutingProvider


def create_routing_provider(name: str, osrm_url: str) -> RoutingProvider:
    """Return the routing provider configured for a route."""
    if name == "waze":
        return WazeRoutingProvider()
    if name == "osrm":
        return OsrmRoutingProvider(osrm_url)
    raise ValueError(f"Unsupported routing provider: {name}")


__all__ = [
    "OsrmRoutingProvider",
    "RoutingError",
    "RoutingProvider",
    "WazeRoutingProvider",
    "create_routing_provider",
]
