"""Waze routing provider (travel time with live traffic)."""

from __future__ import annotations

import logging

import httpx
from aiohttp import ClientSession
from pywaze.route_calculator import WRCError, WazeRouteCalculator

from ..models import Route
from .base import RoutingError, RoutingProvider

_LOGGER = logging.getLogger(__name__)

#: Waze region used for the routing request. Spain belongs to the EU region.
WAZE_REGION = "EU"


class WazeRoutingProvider(RoutingProvider):
    """Resolve routes with Waze's live-traffic routing."""

    name = "waze"

    async def async_get_route(
        self,
        session: ClientSession,
        origin: tuple[float, float],
        destination: tuple[float, float],
    ) -> Route:
        """Return the fastest route between two points, including traffic."""
        lat1, lon1 = origin
        lat2, lon2 = destination

        try:
            async with WazeRouteCalculator(region=WAZE_REGION) as client:
                routes = await client.get_routes(
                    {"lat": lat1, "lon": lon1, "bounds": {}},
                    {"lat": lat2, "lon": lon2, "bounds": {}},
                    alternatives=1,
                )
        except WRCError as err:
            raise RoutingError(f"Waze could not calculate the route: {err}") from err
        except httpx.HTTPError as err:
            raise RoutingError(f"Could not reach Waze: {err}") from err

        if not routes:
            raise RoutingError("Waze returned no routes")

        route = routes[0]
        results = route.get("results") or route.get("result") or []
        if not results:
            raise RoutingError("Waze returned an empty route")

        try:
            coordinates = [(lat1, lon1)]
            duration_s = 0.0
            distance_m = 0.0
            for segment in results:
                path = segment.get("path")
                if path and "x" in path and "y" in path:
                    coordinates.append((float(path["y"]), float(path["x"])))
                duration_s += float(
                    segment.get("crossTime", segment.get("cross_time", 0))
                )
                distance_m += float(segment.get("length", 0))
            coordinates.append((lat2, lon2))
        except (KeyError, TypeError, ValueError) as err:
            raise RoutingError(f"Unexpected Waze response: {err}") from err

        if len(coordinates) < 2 or duration_s <= 0 or distance_m <= 0:
            raise RoutingError("Waze returned incomplete route data")

        return Route(
            coordinates=tuple(coordinates),
            distance_m=distance_m,
            duration_s=duration_s,
            provider=self.name,
        )
