"""Shared entity base for the Route Traffic integration."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, NAME
from .coordinator import RouteTrafficCoordinator


class RouteTrafficEntity(CoordinatorEntity[RouteTrafficCoordinator]):
    """Common base for route traffic entities."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: RouteTrafficCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._entry = entry
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title or NAME,
            manufacturer=MANUFACTURER,
            model="Route corridor monitor",
        )

    @property
    def _data(self) -> dict[str, Any]:
        """Return the coordinator data, defaulting to an empty mapping."""
        return self.coordinator.data or {}

    @property
    def available(self) -> bool:
        """Return False when the coordinator has no usable data."""
        return super().available and bool(self._data)
