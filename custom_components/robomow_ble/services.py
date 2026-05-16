"""Service registrations for the Robomow BLE integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

import voluptuous as vol
from homeassistant.components.lawn_mower.const import DOMAIN as LAWN_MOWER_DOMAIN
from homeassistant.config_entries import ConfigEntryState
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import service

from custom_components.robomow_ble.const import DOMAIN, LOGGER

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant, ServiceCall

    from custom_components.robomow_ble.lawn_mower import RoboMowLawnMowerEntity

SERVICE_START_MOWING = "start_mowing"
ATTR_TARGET = "target"
ATTR_STARTING_ZONE = "starting_zone"
ATTR_DURATION = "duration"


def async_register_services(hass: HomeAssistant) -> None:
    """Register domain services."""
    if hass.services.has_service(DOMAIN, SERVICE_START_MOWING):
        return

    service.async_register_platform_entity_service(
        hass,
        DOMAIN,
        SERVICE_START_MOWING,
        entity_domain=LAWN_MOWER_DOMAIN,
        func=async_handle_start_mowing,
        schema=cv.make_entity_service_schema(
            {
                vol.Optional(ATTR_STARTING_ZONE, default=0x80): vol.All(
                    vol.Coerce(int), vol.Range(min=0, max=0xFF)
                ),
                vol.Optional(ATTR_DURATION, default=30): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=0xFF)
                ),
            }
        ),
    )


def async_unregister_services_if_unused(hass: HomeAssistant) -> None:
    """Unregister domain services when there are no loaded entries left."""
    has_loaded_entries = any(
        entry.state is ConfigEntryState.LOADED
        for entry in hass.config_entries.async_entries(DOMAIN)
    )

    if not has_loaded_entries and hass.services.has_service(
        DOMAIN, SERVICE_START_MOWING
    ):
        hass.services.async_remove(DOMAIN, SERVICE_START_MOWING)


async def async_handle_start_mowing(
    entity: RoboMowLawnMowerEntity, call: ServiceCall
) -> None:
    """Handle robomow_ble.start_mowing service calls."""
    await entity.async_start_mowing(
        duration_minutes=call.data.get(ATTR_DURATION),
        starting_zone=call.data.get(ATTR_STARTING_ZONE),
    )
