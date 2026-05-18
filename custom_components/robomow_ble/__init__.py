#!/usr/bin/env python3
"""Support for Robomow via Bluetooth."""

# ruff: noqa: E402

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

from homeassistant.const import Platform


# TODO(AM): Remove this hack once we have proper packages published to PyPI.
def _ensure_package_import_path() -> None:
    """Allow local monorepo package imports during development."""
    package_src = (
        Path(__file__).resolve().parents[2] / "packages" / "robomow_ble" / "src"
    )
    if package_src.exists() and str(package_src) not in sys.path:
        sys.path.insert(0, str(package_src))


_ensure_package_import_path()

from .const import LOGGER
from .coordinator import RobomowCoordinator
from .services import async_register_services, async_unregister_services_if_unused

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .coordinator import RobomowConfigEntry

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
    async_register_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: RobomowConfigEntry) -> bool:
    """Set up a Robomow BLE device from a config entry."""
    LOGGER.debug("Setting up config entry %s", entry.entry_id)

    coordinator = RobomowCoordinator(hass, entry)
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(coordinator.async_start())

    return True


async def async_unload_entry(hass: HomeAssistant, entry: RobomowConfigEntry) -> bool:
    """Unload a config entry."""
    LOGGER.debug("Unloading config entry %s", entry.entry_id)

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        async_unregister_services_if_unused(hass)
        coordinator: RobomowCoordinator = entry.runtime_data
        await coordinator.async_shutdown()

    return unload_ok
