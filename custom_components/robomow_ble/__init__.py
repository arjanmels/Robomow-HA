#!/usr/bin/env python3
"""Support for Robomow via Bluetooth."""
# ruff: noqa: PLC0415

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

from homeassistant.const import Platform
from homeassistant.exceptions import ConfigEntryError


def _ensure_package_import_path() -> None:
    """Allow local monorepo package imports during development."""
    package_src = (
        Path(__file__).resolve().parents[2] / "packages" / "robomow_ble" / "src"
    )
    if package_src.exists() and str(package_src) not in sys.path:
        sys.path.insert(0, str(package_src))


_ensure_package_import_path()

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .coordinator import RoboMowConfigEntry

PLATFORMS: list[Platform] = [
    Platform.LAWN_MOWER,
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.SELECT,
    Platform.NUMBER,
    Platform.SWITCH,
]


async def async_setup(hass: HomeAssistant, _config: dict) -> bool:
    """Set up the Robomow BLE component."""
    from .services import async_register_services

    async_register_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: RoboMowConfigEntry) -> bool:
    """Set up a Robomow BLE device from a config entry."""
    from .const import CONF_MAINBOARD_SERIAL, DOMAIN, LOGGER
    from .coordinator import RoboMowCoordinator

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

    entry.runtime_data = RoboMowCoordinator(hass, address, mainboard_serial, entry)

    try:
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    except Exception:
        await entry.runtime_data.async_shutdown()
        raise

    entry.async_on_unload(entry.runtime_data.async_start())
    return True


async def async_unload_entry(hass: HomeAssistant, entry: RoboMowConfigEntry) -> bool:
    """Unload a config entry."""
    from .services import async_unregister_services_if_unused

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        await entry.runtime_data.async_shutdown()
        async_unregister_services_if_unused(hass)
    return unload_ok
