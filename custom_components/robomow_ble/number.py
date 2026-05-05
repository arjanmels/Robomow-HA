"""Support for Robomow BLE number inputs."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.number import NumberEntity, NumberMode

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
    """Set up the Robomow BLE number entities."""
    LOGGER.debug("Setting up number platform for config entry %s", entry.entry_id)
    coordinator = entry.runtime_data
    async_add_entities([RoboMowMowingDurationNumber(coordinator)])


class RoboMowMowingDurationNumber(RoboMowBLECoordinatorEntity, NumberEntity):
    """Representation of a Robomow mowing duration number input."""

    _attr_has_entity_name = True
    _attr_name = "Mowing duration"
    _attr_native_min_value = 1.0
    _attr_native_max_value = 255.0
    _attr_native_step = 1.0
    _attr_native_unit_of_measurement = "min"
    _attr_entity_category = None
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator: RoboMowBLECoordinator) -> None:
        """Initialize the number input."""
        self._init_coordinator_entity(coordinator)
        self._attr_unique_id = f"{DOMAIN}_{coordinator.address}_mowing_duration"
        self._attr_native_value = float(coordinator.device.mowing_duration)

    async def async_set_native_value(self, value: float) -> None:
        """Set the mowing duration."""
        self.coordinator.device.mowing_duration = int(value)
        self._attr_native_value = value
        self.async_write_ha_state()
        LOGGER.debug(
            "Set mowing duration to %d minutes for %s",
            int(value),
            self.coordinator.address,
        )
