"""Coordinator that resolves a route and matches incidents against it."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_CORRIDOR_RADIUS,
    CONF_DESTINATION,
    CONF_ORIGIN,
    CONF_OSRM_URL,
    CONF_PROVIDERS,
    CONF_ROUTING,
    CONF_UPDATE_INTERVAL,
    DEFAULT_CORRIDOR_RADIUS,
    DEFAULT_OSRM_URL,
    DEFAULT_PROVIDERS,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    SEVERITY_ORDER,
)
from .geometry import RouteGeometry
from .models import Incident, Route
from .providers import PROVIDERS, IncidentError
from .routing import OsrmRoutingProvider, RoutingError

_LOGGER = logging.getLogger(__name__)

#: How long a resolved route is reused before asking the routing provider
#: again. Routes change rarely, incidents change constantly.
ROUTE_CACHE_TTL = timedelta(hours=6)


class RouteTrafficCoordinator(DataUpdateCoordinator[dict]):
    """Poll the route and its incidents."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.entry = entry
        self.origin = entry.data[CONF_ORIGIN]
        self.destination = entry.data[CONF_DESTINATION]

        options = entry.options
        self.corridor_radius = float(
            options.get(CONF_CORRIDOR_RADIUS, DEFAULT_CORRIDOR_RADIUS)
        )
        self.interval = int(options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL))

        provider_names = options.get(CONF_PROVIDERS) or DEFAULT_PROVIDERS
        self.providers = [
            PROVIDERS[name]() for name in provider_names if name in PROVIDERS
        ]

        routing_name = options.get(CONF_ROUTING, "osrm")
        if routing_name != "osrm":
            raise ValueError(f"Unsupported routing provider: {routing_name}")
        self.routing = OsrmRoutingProvider(
            options.get(CONF_OSRM_URL, DEFAULT_OSRM_URL)
        )

        self._route: Route | None = None
        self._geometry: RouteGeometry | None = None
        self._route_fetched_at = None

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=self.interval),
        )

    async def _async_update_data(self) -> dict:
        """Fetch the route and every incident, then match them."""
        session = async_get_clientsession(self.hass)

        try:
            await self._async_ensure_route(session)
        except RoutingError as err:
            raise UpdateFailed(f"Could not resolve the route: {err}") from err

        assert self._route is not None
        assert self._geometry is not None

        incidents: list[Incident] = []
        failed: list[str] = []

        for provider in self.providers:
            try:
                fetched = await provider.async_fetch_incidents(session)
            except IncidentError as err:
                _LOGGER.warning("Provider %s failed: %s", provider.name, err)
                failed.append(provider.name)
                continue
            except Exception:  # noqa: BLE001 - a bad provider must not kill the poll
                _LOGGER.exception("Unexpected error in provider %s", provider.name)
                failed.append(provider.name)
                continue
            incidents.extend(fetched)

        # Match every incident to the route corridor.
        matched: list[Incident] = []
        for incident in incidents:
            distance = self._geometry.nearest_distance_m(
                incident.points, self.corridor_radius
            )
            if distance > self.corridor_radius:
                continue
            matched.append(
                Incident(
                    uid=incident.uid,
                    provider=incident.provider,
                    road=incident.road,
                    severity=incident.severity,
                    cause=incident.cause,
                    detail=incident.detail,
                    management=incident.management,
                    is_closure=incident.is_closure,
                    municipality=incident.municipality,
                    started_at=incident.started_at,
                    points=incident.points,
                    distance_m=distance,
                )
            )

        matched.sort(key=lambda item: (not item.is_closure, item.distance_m))

        closures = [item for item in matched if item.is_closure]
        worst = "unknown"
        for item in matched:
            if SEVERITY_ORDER.get(item.severity, 0) > SEVERITY_ORDER.get(worst, 0):
                worst = item.severity

        return {
            "route": self._route,
            "incidents": matched,
            "closures": closures,
            "count": len(matched),
            "closure_count": len(closures),
            "worst_severity": worst,
            "roads": sorted({item.road for item in matched if item.road}),
            "failed_providers": failed,
            "corridor_radius": self.corridor_radius,
        }

    async def _async_ensure_route(self, session) -> None:
        """Resolve the route, reusing it until the cache expires."""
        now = self.hass.loop.time()
        if (
            self._route is not None
            and self._geometry is not None
            and self._route_fetched_at is not None
            and now - self._route_fetched_at < ROUTE_CACHE_TTL.total_seconds()
        ):
            return

        origin = self._resolve(self.origin)
        destination = self._resolve(self.destination)
        if origin is None or destination is None:
            raise RoutingError(
                f"Cannot resolve origin {self.origin!r} or destination "
                f"{self.destination!r} to coordinates"
            )

        route = await self.routing.async_get_route(session, origin, destination)
        self._route = route
        self._geometry = RouteGeometry(route.coordinates)
        self._route_fetched_at = now
        _LOGGER.debug(
            "Route resolved: %.1f km via %s", route.distance_km, route.provider
        )

    def _resolve(self, reference: str) -> tuple[float, float] | None:
        """Resolve ``zone.home``, ``device_tracker.x`` or ``lat,lon``."""
        reference = (reference or "").strip()
        if not reference:
            return None

        if "," in reference:
            parts = [part.strip() for part in reference.split(",")]
            if len(parts) == 2:
                try:
                    return float(parts[0]), float(parts[1])
                except ValueError:
                    pass

        state = self.hass.states.get(reference)
        if state is None:
            return None
        try:
            return float(state.attributes["latitude"]), float(
                state.attributes["longitude"]
            )
        except (KeyError, TypeError, ValueError):
            return None
