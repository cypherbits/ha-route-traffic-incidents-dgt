"""OSRM routing provider (public demo server or any self-hosted instance)."""

from __future__ import annotations

import logging
from datetime import timedelta

from aiohttp import ClientError, ClientSession

from ..models import Route
from .base import RoutingError, RoutingProvider

_LOGGER = logging.getLogger(__name__)

REQUEST_TIMEOUT = 25


class OsrmRoutingProvider(RoutingProvider):
    """Resolve routes with an OSRM server."""

    name = "osrm"
    route_cache_ttl = timedelta(hours=6)

    def __init__(self, base_url: str) -> None:
        """Initialize with the OSRM base URL."""
        self._base_url = base_url.rstrip("/")

    async def async_get_route(
        self,
        session: ClientSession,
        origin: tuple[float, float],
        destination: tuple[float, float],
    ) -> Route:
        """Return the driving route between two points."""
        lat1, lon1 = origin
        lat2, lon2 = destination
        url = (
            f"{self._base_url}/route/v1/driving/"
            f"{lon1},{lat1};{lon2},{lat2}"
            "?overview=full&geometries=geojson&alternatives=false&steps=false"
        )

        try:
            async with session.get(url, timeout=REQUEST_TIMEOUT) as resp:
                if resp.status != 200:
                    raise RoutingError(f"OSRM responded with HTTP {resp.status}")
                payload = await resp.json()
        except ClientError as err:
            raise RoutingError(f"Could not reach OSRM: {err}") from err
        except TimeoutError as err:
            raise RoutingError("OSRM request timed out") from err

        if payload.get("code") != "Ok" or not payload.get("routes"):
            raise RoutingError(
                f"OSRM could not find a route: {payload.get('message', payload.get('code'))}"
            )

        route = payload["routes"][0]
        coordinates = route.get("geometry", {}).get("coordinates") or []
        if len(coordinates) < 2:
            raise RoutingError("OSRM returned an empty geometry")

        return Route(
            coordinates=tuple((float(lon), float(lat)) for lon, lat in coordinates),
            distance_m=float(route.get("distance", 0.0)),
            duration_s=float(route.get("duration", 0.0)),
            provider=self.name,
        )
