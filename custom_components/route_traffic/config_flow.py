"""Config flow for the Route Traffic integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers import selector

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
    INCIDENT_PROVIDERS,
    MAX_CORRIDOR_RADIUS,
    MAX_UPDATE_INTERVAL,
    MIN_CORRIDOR_RADIUS,
    MIN_UPDATE_INTERVAL,
    ROUTING_PROVIDERS,
)

_LOGGER = logging.getLogger(__name__)

LOCATION_SELECTOR = selector.TextSelector()


class RouteTrafficConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the initial configuration."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for the origin and destination of the route."""
        errors: dict[str, str] = {}

        if user_input is not None:
            origin = user_input[CONF_ORIGIN].strip()
            destination = user_input[CONF_DESTINATION].strip()

            if not self._looks_resolvable(origin):
                errors[CONF_ORIGIN] = "invalid_location"
            if not self._looks_resolvable(destination):
                errors[CONF_DESTINATION] = "invalid_location"

            if not errors:
                await self.async_set_unique_id(f"{origin}->{destination}".lower())
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"{origin.split('.')[-1]} → {destination.split('.')[-1]}",
                    data={CONF_ORIGIN: origin, CONF_DESTINATION: destination},
                    options={
                        CONF_CORRIDOR_RADIUS: DEFAULT_CORRIDOR_RADIUS,
                        CONF_UPDATE_INTERVAL: DEFAULT_UPDATE_INTERVAL,
                        CONF_PROVIDERS: DEFAULT_PROVIDERS,
                        CONF_ROUTING: "osrm",
                        CONF_OSRM_URL: DEFAULT_OSRM_URL,
                    },
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_ORIGIN): LOCATION_SELECTOR,
                vol.Required(CONF_DESTINATION): LOCATION_SELECTOR,
            }
        )
        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    def _looks_resolvable(self, reference: str) -> bool:
        """Return True when the reference is an entity or a coordinate pair."""
        if not reference:
            return False
        if "," in reference:
            parts = [part.strip() for part in reference.split(",")]
            if len(parts) == 2:
                try:
                    float(parts[0])
                    float(parts[1])
                    return True
                except ValueError:
                    return False
        return self.hass.states.get(reference) is not None

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return the options flow."""
        return RouteTrafficOptionsFlow()


class RouteTrafficOptionsFlow(OptionsFlow):
    """Tune the corridor, providers and refresh interval."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show and store the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = self.config_entry.options

        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_CORRIDOR_RADIUS,
                    default=options.get(
                        CONF_CORRIDOR_RADIUS, DEFAULT_CORRIDOR_RADIUS
                    ),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=MIN_CORRIDOR_RADIUS,
                        max=MAX_CORRIDOR_RADIUS,
                        step=25,
                        unit_of_measurement="m",
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Optional(
                    CONF_UPDATE_INTERVAL,
                    default=options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=MIN_UPDATE_INTERVAL,
                        max=MAX_UPDATE_INTERVAL,
                        step=30,
                        unit_of_measurement="s",
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Optional(
                    CONF_PROVIDERS,
                    default=options.get(CONF_PROVIDERS, DEFAULT_PROVIDERS),
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=list(INCIDENT_PROVIDERS),
                        multiple=True,
                        mode=selector.SelectSelectorMode.LIST,
                        translation_key=CONF_PROVIDERS,
                    )
                ),
                vol.Optional(
                    CONF_ROUTING,
                    default=options.get(CONF_ROUTING, "osrm"),
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=list(ROUTING_PROVIDERS),
                        mode=selector.SelectSelectorMode.DROPDOWN,
                        translation_key=CONF_ROUTING,
                    )
                ),
                vol.Optional(
                    CONF_OSRM_URL,
                    default=options.get(CONF_OSRM_URL, DEFAULT_OSRM_URL),
                ): selector.TextSelector(),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
