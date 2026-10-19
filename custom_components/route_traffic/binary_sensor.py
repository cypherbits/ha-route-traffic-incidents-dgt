"""Binary sensor entities for the Route Traffic integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
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
    """Set up the binary sensors for a config entry."""
    coordinator: RouteTrafficCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([RouteBlockedBinarySensor(coordinator, entry)])


class RouteBlockedBinarySensor(RouteTrafficEntity, BinarySensorEntity):
    """Whether the route is currently blocked by a closure."""

    _attr_translation_key = "route_blocked"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_icon = "mdi:road-variant"

    def __init__(
        self, coordinator: RouteTrafficCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_route_blocked"

    @property
    def is_on(self) -> bool:
        """Return True when at least one closure affects the route."""
        return bool(self._data.get("closure_count", 0))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the closures blocking the route."""
        return {
            "closures": [
                item.as_dict() for item in self._data.get("closures", [])
            ]
        }
