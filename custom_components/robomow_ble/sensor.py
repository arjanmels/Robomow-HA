"""Support for Robomow BLE sensors."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.sensor import (
    SensorEntity,
)

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
    """Set up the Robomow BLE sensors."""
    LOGGER.debug("Setting up sensor platform for config entry %s", entry.entry_id)
    coordinator = entry.runtime_data
    async_add_entities(
        [
            RoboMowBLEStatusSensorEntity(coordinator),
            RoboMowBLEOperatingStateSensorEntity(coordinator),
        ]
    )


class RoboMowBLEStatusSensorEntity(RoboMowBLECoordinatorEntity, SensorEntity):
    """Representation of a Robomow BLE status text sensor."""

    _attr_has_entity_name = True
    _attr_name = "Status"

    def __init__(self, coordinator: RoboMowBLECoordinator) -> None:
        """Initialize the status sensor."""
        self._init_coordinator_entity(coordinator)
        self._attr_unique_id = f"{DOMAIN}_{coordinator.address}_status"

    @property
    def native_value(self) -> str | None:
        """Return the current mower status text."""
        return self.coordinator.device.status


class RoboMowBLEOperatingStateSensorEntity(RoboMowBLECoordinatorEntity, SensorEntity):
    """Representation of a Robomow BLE operating state text sensor."""

    _attr_has_entity_name = True
    _attr_name = "Operating state"

    def __init__(self, coordinator: RoboMowBLECoordinator) -> None:
        """Initialize the operating state sensor."""
        self._init_coordinator_entity(coordinator)
        self._attr_unique_id = f"{DOMAIN}_{coordinator.address}_operating_state"

    @property
    def native_value(self) -> str | None:
        """Return the current mower operating state text."""
        return self.coordinator.device.operating_state
