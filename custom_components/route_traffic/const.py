"""Constants for the Route Traffic integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "route_traffic"
NAME: Final = "Route Traffic"
MANUFACTURER: Final = "Route Traffic"

CONF_ORIGIN: Final = "origin"
CONF_DESTINATION: Final = "destination"
CONF_CORRIDOR_RADIUS: Final = "corridor_radius"
CONF_UPDATE_INTERVAL: Final = "update_interval"
CONF_PROVIDERS: Final = "providers"
CONF_ROUTING: Final = "routing"
CONF_OSRM_URL: Final = "osrm_url"

DEFAULT_NAME: Final = "Route"
DEFAULT_CORRIDOR_RADIUS: Final = 300.0
DEFAULT_UPDATE_INTERVAL: Final = 300
DEFAULT_ROUTING: Final = "waze"
DEFAULT_OSRM_URL: Final = "https://router.project-osrm.org"
DEFAULT_PROVIDERS: Final = ["dgt"]

MIN_CORRIDOR_RADIUS: Final = 25.0
MAX_CORRIDOR_RADIUS: Final = 5000.0
MIN_UPDATE_INTERVAL: Final = 60
MAX_UPDATE_INTERVAL: Final = 86400

# Providers that ship with the integration.
INCIDENT_PROVIDERS: Final[dict[str, str]] = {
    "dgt": "DGT (Spain, DATEX II)",
}

ROUTING_PROVIDERS: Final[dict[str, str]] = {
    "waze": "Waze (live traffic)",
    "osrm": "OSRM (free-flow, no API key)",
}

SEVERITY_ORDER: Final[dict[str, int]] = {
    "unknown": 0,
    "lowest": 1,
    "low": 2,
    "medium": 3,
    "high": 4,
    "highest": 5,
}

# Values of DATEX II roadOrCarriagewayOrLaneManagementType that mean a closure.
CLOSURE_MANAGEMENT: Final[frozenset[str]] = frozenset(
    {
        "roadClosed",
        "allLanesCompleteCarriageway",
        "laneClosures",
        "intermittentShortTermClosures",
    }
)
