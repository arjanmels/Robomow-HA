#!/usr/bin/env python3
"""Support for Robomow via Bluetooth."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.components.bluetooth import BluetoothScanningMode
from homeassistant.const import Platform
from homeassistant.exceptions import ConfigEntryError
from regex import P

from custom_components.robomow_ble.const import CONF_MAINBOARD_SERIAL, DOMAIN, LOGGER

from .coordinator import (
    RoboMowBLEConfigEntry,
    RoboMowBLECoordinator,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.SWITCH]

_LOGGER = logging.getLogger(__name__)


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

    entry.runtime_data = coordinator = RoboMowBLECoordinator(
        hass, address, mainboard_serial
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(coordinator.async_start())
    return True


async def async_unload_entry(hass: HomeAssistant, entry: RoboMowBLEConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
