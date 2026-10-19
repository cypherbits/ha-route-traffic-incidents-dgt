"""Routing providers resolve a pair of coordinates into a route polyline."""

from __future__ import annotations

import abc
from datetime import timedelta

from aiohttp import ClientSession

from ..models import Route


class RoutingError(Exception):
    """Raised when a route cannot be resolved."""


class RoutingProvider(abc.ABC):
    """Base class for routing providers."""

    name: str = ""
    route_cache_ttl: timedelta = timedelta(0)

    @abc.abstractmethod
    async def async_get_route(
        self,
        session: ClientSession,
        origin: tuple[float, float],
        destination: tuple[float, float],
    ) -> Route:
        """Return a route between two ``(latitude, longitude)`` points."""
