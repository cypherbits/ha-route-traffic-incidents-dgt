#!/usr/bin/env python3
"""Offline smoke test for the Route Traffic integration.

Exercises the real modules (geometry, OSRM routing and the DGT provider)
without Home Assistant, using a small stub package for ``homeassistant``.

Usage:
    python3 tools/smoke_test.py [lat1,lon1] [lat2,lon2]
"""

from __future__ import annotations

import asyncio
import sys
import types
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "custom_components"))

# --------------------------------------------------------------------------
# Minimal Home Assistant stubs, enough to import the modules under test.
# --------------------------------------------------------------------------
for name in (
    "homeassistant",
    "homeassistant.config_entries",
    "homeassistant.const",
    "homeassistant.core",
    "homeassistant.exceptions",
    "homeassistant.helpers",
    "homeassistant.helpers.aiohttp_client",
    "homeassistant.helpers.update_coordinator",
    "homeassistant.helpers.device_registry",
):
    sys.modules.setdefault(name, types.ModuleType(name))

sys.modules["homeassistant.const"].Platform = type(
    "Platform", (), {"SENSOR": "sensor", "BINARY_SENSOR": "binary_sensor"}
)
sys.modules["homeassistant.config_entries"].ConfigEntry = type("ConfigEntry", (), {})
sys.modules["homeassistant.core"].HomeAssistant = type("HomeAssistant", (), {})
sys.modules["homeassistant.exceptions"].ConfigEntryError = type(
    "ConfigEntryError", (Exception,), {}
)
sys.modules["homeassistant.helpers.aiohttp_client"].async_get_clientsession = (
    lambda hass: None
)


class _Coordinator:
    def __init__(self, *args, **kwargs):
        pass

    def __class_getitem__(cls, item):
        return cls


class _UpdateFailed(Exception):
    pass


sys.modules["homeassistant.helpers.update_coordinator"].DataUpdateCoordinator = (
    _Coordinator
)
sys.modules["homeassistant.helpers.update_coordinator"].UpdateFailed = _UpdateFailed
sys.modules["homeassistant.helpers.device_registry"].DeviceInfo = dict

import aiohttp  # noqa: E402

from route_traffic.geometry import RouteGeometry  # noqa: E402
from route_traffic.providers.dgt import parse_feed  # noqa: E402
from route_traffic.routing.osrm import OsrmRoutingProvider  # noqa: E402

DGT_FEED = "https://nap.dgt.es/datex2/v3/dgt/SituationPublication/datex2_v37.xml"


def parse_pair(raw: str) -> tuple[float, float]:
    """Parse ``lat,lon`` into a tuple."""
    lat, lon = raw.split(",")
    return float(lat), float(lon)


async def main() -> int:
    """Run the smoke test."""
    origin = parse_pair(sys.argv[1]) if len(sys.argv) > 2 else (38.78313, 0.15221)
    destination = parse_pair(sys.argv[2]) if len(sys.argv) > 2 else (38.71735, 0.14065)

    print(f"Route: {origin} -> {destination}")

    routing = OsrmRoutingProvider("https://router.project-osrm.org")
    async with aiohttp.ClientSession() as session:
        route = await routing.async_get_route(session, origin, destination)
        print(
            f"  OSRM: {route.distance_km} km / {route.duration_min} min "
            f"({len(route.coordinates)} points)"
        )

        geometry = RouteGeometry(route.coordinates)
        print(f"  polyline length: {geometry.length_m / 1000:.2f} km")

        print("Downloading the DGT feed...")
        req = urllib.request.Request(DGT_FEED, headers={"User-Agent": "smoke-test"})
        with urllib.request.urlopen(req, timeout=120) as resp:
            blob = resp.read()
        print(f"  feed: {len(blob) / 1_000_000:.1f} MB")

        incidents = parse_feed(blob)
        print(f"  parsed incidents (all Spain): {len(incidents)}")

    for radius in (200, 300, 500, 1000):
        matched = []
        for incident in incidents:
            distance = geometry.nearest_distance_m(incident.points, radius)
            if distance <= radius:
                matched.append((distance, incident))
        matched.sort(key=lambda item: item[0])
        closures = [item for item in matched if item[1].is_closure]
        print(
            f"\n  radius {radius} m -> {len(matched)} incidents, "
            f"{len(closures)} closures"
        )
        for distance, incident in matched[:6]:
            flag = "CLOSURE" if incident.is_closure else "notice "
            print(
                f"    {flag} {incident.road or '?':8s} "
                f"{distance:6.0f} m  {incident.cause or '-':26s} "
                f"{incident.detail or '-':16s} {incident.municipality}"
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
