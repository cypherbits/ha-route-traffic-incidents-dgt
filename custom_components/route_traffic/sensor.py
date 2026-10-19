"""Sensor entities for the Route Traffic integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfLength, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import RouteTrafficCoordinator
from .entity import RouteTrafficEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensors for a config entry."""
    coordinator: RouteTrafficCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            ClosuresSensor(coordinator, entry),
            IncidentsSensor(coordinator, entry),
            WorstSeveritySensor(coordinator, entry),
            AffectedRoadsSensor(coordinator, entry),
            RouteDistanceSensor(coordinator, entry),
            RouteDurationSensor(coordinator, entry),
        ]
    )


class ClosuresSensor(RouteTrafficEntity, SensorEntity):
    """Number of road closures inside the route corridor."""

    _attr_translation_key = "closures"
    _attr_icon = "mdi:road-variant"

    def __init__(
        self, coordinator: RouteTrafficCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_closures"

    @property
    def native_value(self) -> int:
        """Return the number of closures."""
        return int(self._data.get("closure_count", 0))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the matching incidents."""
        data = self._data
        return {
            "closures": [item.as_dict() for item in data.get("closures", [])],
            "incidents": [item.as_dict() for item in data.get("incidents", [])],
            "corridor_radius_m": data.get("corridor_radius"),
            "failed_providers": data.get("failed_providers", []),
            "origin": self._entry.data.get("origin"),
            "destination": self._entry.data.get("destination"),
        }


class IncidentsSensor(RouteTrafficEntity, SensorEntity):
    """Number of incidents (closures included) inside the route corridor."""

    _attr_translation_key = "incidents"
    _attr_icon = "mdi:traffic-light"

    def __init__(
        self, coordinator: RouteTrafficCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_incidents"

    @property
    def native_value(self) -> int:
        """Return the number of incidents."""
        return int(self._data.get("count", 0))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the roads with incidents on this route."""
        return {"roads": self._data.get("roads", [])}


class WorstSeveritySensor(RouteTrafficEntity, SensorEntity):
    """Highest severity among the incidents on the route."""

    _attr_translation_key = "worst_severity"
    _attr_icon = "mdi:alert-circle-outline"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = ["unknown", "lowest", "low", "medium", "high", "highest"]

    def __init__(
        self, coordinator: RouteTrafficCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_worst_severity"

    @property
    def native_value(self) -> str:
        """Return the worst severity."""
        return str(self._data.get("worst_severity", "unknown"))


class AffectedRoadsSensor(RouteTrafficEntity, SensorEntity):
    """Roads with incidents on the route."""

    _attr_translation_key = "affected_roads"
    _attr_icon = "mdi:highway"

    def __init__(
        self, coordinator: RouteTrafficCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_affected_roads"

    @property
    def native_value(self) -> str:
        """Return the affected roads, comma separated."""
        roads = self._data.get("roads", [])
        return ", ".join(roads) if roads else "none"


class RouteDistanceSensor(RouteTrafficEntity, SensorEntity):
    """Length of the monitored route."""

    _attr_translation_key = "route_distance"
    _attr_icon = "mdi:map-marker-distance"
    _attr_device_class = SensorDeviceClass.DISTANCE
    _attr_native_unit_of_measurement = UnitOfLength.KILOMETERS
    _attr_suggested_display_precision = 1

    def __init__(
        self, coordinator: RouteTrafficCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_route_distance"

    @property
    def native_value(self) -> float | None:
        """Return the route distance in kilometers."""
        route = self._data.get("route")
        return round(route.distance_m / 1000, 2) if route else None


class RouteDurationSensor(RouteTrafficEntity, SensorEntity):
    """Estimated driving time for the monitored route."""

    _attr_translation_key = "route_duration"
    _attr_icon = "mdi:clock-outline"
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_suggested_display_precision = 0

    def __init__(
        self, coordinator: RouteTrafficCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_route_duration"

    @property
    def native_value(self) -> float | None:
        """Return the estimated duration in minutes."""
        route = self._data.get("route")
        return round(route.duration_s / 60, 1) if route else None
