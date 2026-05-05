#!/usr/bin/env python3
"""Support for Robomow via Bluetooth."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.const import Platform
from homeassistant.exceptions import ConfigEntryError

from custom_components.robomow_ble.const import CONF_MAINBOARD_SERIAL, DOMAIN, LOGGER

from .coordinator import (
    RoboMowBLEConfigEntry,
    RoboMowBLECoordinator,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.BUTTON,
    Platform.NUMBER,
]


async def async_setup_entry(hass: HomeAssistant, entry: RoboMowBLEConfigEntry) -> bool:
    """Set up a Robomow BLE device from a config entry."""
    LOGGER.debug("Setting up config entry (async_setup_entry) %s", entry.entry_id)
    address = entry.unique_id
    if address is None:
        raise ConfigEntryError(
            translation_domain=DOMAIN, translation_key="no_unique_address"
        )

    mainboard_serial = entry.data.get(CONF_MAINBOARD_SERIAL)
    if mainboard_serial is None:
        raise ConfigEntryError(
            translation_domain=DOMAIN, translation_key="no_mainboard_serial"
        )

    entry.runtime_data = RoboMowBLECoordinator(hass, address, mainboard_serial)

    try:
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    except Exception:
        await entry.runtime_data.async_shutdown()
        raise

    entry.async_on_unload(entry.runtime_data.async_start())
    return True


async def async_unload_entry(hass: HomeAssistant, entry: RoboMowBLEConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        await entry.runtime_data.async_shutdown()
    return unload_ok
