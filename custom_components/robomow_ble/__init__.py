"""Support for Robomow via Bluetooth."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.const import Platform
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN, LOGGER
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

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


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
