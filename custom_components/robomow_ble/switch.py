"""Support for Robomow BLE switches."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.const import EntityCategory
from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH

from .const import DOMAIN, LOGGER

if TYPE_CHECKING:
    from collections.abc import Callable

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


class RoboMowProgramEnabledSwitch(SwitchEntity):
    """Representation of a Robomow program enabled switch."""

    _attr_device_class = SwitchDeviceClass.SWITCH
    _attr_entity_category = EntityCategory.CONFIG
    _attr_has_entity_name = True
    _attr_name = "Program enabled"
    _attr_unique_id_suffix = "program_enabled"

    def __init__(self, coordinator: RoboMowBLECoordinator) -> None:
        """Initialize the switch."""
        self.coordinator = coordinator
        self._remove_state_listener: Callable[[], None] | None = None
        self._attr_unique_id = (
            f"{DOMAIN}_{coordinator.address}_program_enabled"
        )

    async def async_added_to_hass(self) -> None:
        """Register for BLE state updates when added to Home Assistant."""
        await super().async_added_to_hass()
        self._remove_state_listener = self.coordinator.device.add_state_listener(
            self._handle_device_state_update
        )

    async def async_will_remove_from_hass(self) -> None:
        """Unregister BLE state updates when removed from Home Assistant."""
        if self._remove_state_listener is not None:
            self._remove_state_listener()
            self._remove_state_listener = None
        await super().async_will_remove_from_hass()

    def _handle_device_state_update(self) -> None:
        """Handle BLE state updates from the underlying device."""
        if self.hass is None:
            return
        self.hass.loop.call_soon_threadsafe(self.async_write_ha_state)

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information."""
        return {
            "connections": {(CONNECTION_BLUETOOTH, self.coordinator.address)},
            "identifiers": {(DOMAIN, self.coordinator.address)},
            "name": f"Robomow {self.coordinator.address.replace(':', '').upper()[-4:]}",
            "manufacturer": "RoboMow",
        }

    @property
    def is_on(self) -> bool:
        """Return True if the program is enabled."""
        LOGGER.debug("Checking if program is enabled for %s: %s",
            self.coordinator.address, self.coordinator.device.program_enabled)
        return self.coordinator.device.program_enabled or False

    @property
    def available(self) -> bool:
        """Return True if the device is connected."""
        LOGGER.debug("Checking availability for %s: connected=%s",
            self.coordinator.address, self.coordinator.device.is_connected())
        return self.coordinator.device.is_connected()

    async def async_turn_on(self, **_kwargs: Any) -> None:
        """Turn on the program."""
        LOGGER.debug("Enabling program for %s", self.coordinator.address)
        await self.coordinator.device.enable_program()

    async def async_turn_off(self, **_kwargs: Any) -> None:
        """Turn off the program."""
        LOGGER.debug("Disabling program for %s", self.coordinator.address)
        await self.coordinator.device.disable_program()

