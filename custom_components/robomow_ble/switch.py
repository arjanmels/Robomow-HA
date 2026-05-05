"""Support for Robomow BLE switches."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity

from .const import DOMAIN, LOGGER
from .coordinator import RoboMowBLECoordinatorEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from .coordinator import RoboMowBLEConfigEntry, RoboMowBLECoordinator


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: RoboMowBLEConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Robomow BLE switches."""
    LOGGER.debug("Setting up switch platform for config entry %s", entry.entry_id)
    coordinator = entry.runtime_data
    async_add_entities([RoboMowProgramEnabledSwitch(coordinator)])


class RoboMowProgramEnabledSwitch(RoboMowBLECoordinatorEntity, SwitchEntity):
    """Representation of a Robomow program enabled switch."""

    _attr_device_class = SwitchDeviceClass.SWITCH
    _attr_entity_category = None
    _attr_has_entity_name = True
    _attr_name = "Program enabled"
    _attr_unique_id_suffix = "program_enabled"

    def __init__(self, coordinator: RoboMowBLECoordinator) -> None:
        """Initialize the switch."""
        self._init_coordinator_entity(coordinator)
        self._attr_unique_id = f"{DOMAIN}_{coordinator.address}_program_enabled"

    @property
    def is_on(self) -> bool:
        """Return True if the program is enabled."""
        return self.coordinator.device.program_enabled or False

    async def async_turn_on(self, **_kwargs: Any) -> None:
        """Turn on the program."""
        LOGGER.debug("Enabling program for %s", self.coordinator.address)
        await self.coordinator.device.enable_program()

    async def async_turn_off(self, **_kwargs: Any) -> None:
        """Turn off the program."""
        LOGGER.debug("Disabling program for %s", self.coordinator.address)
        await self.coordinator.device.disable_program()
