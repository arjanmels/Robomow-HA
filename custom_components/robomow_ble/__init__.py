#!/usr/bin/env python3
"""Support for Robomow via Bluetooth."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.components.bluetooth import BluetoothScanningMode
from homeassistant.const import Platform

from .coordinator import (
    RoboMowBLEConfigEntry,
    RoboMowBLECoordinator,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

PLATFORMS: list[Platform] = [Platform.SENSOR]

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: RoboMowBLEConfigEntry) -> bool:
    """Set up a Robomow BLE device from a config entry."""
    address = entry.unique_id
    if address is None:
        _LOGGER.error("Cannot set up Robomow BLE entry without a unique_id")
        return False

    entry.runtime_data = coordinator = RoboMowBLECoordinator(
        hass,
        _LOGGER,
        address=address,
        mode=BluetoothScanningMode.ACTIVE,
    )
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    # only start after all platforms have had a chance to subscribe
    entry.async_on_unload(coordinator.async_start())
    return True


async def async_unload_entry(hass: HomeAssistant, entry: RoboMowBLEConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
