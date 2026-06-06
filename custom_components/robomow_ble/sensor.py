"""Support for Robomow BLE sensors."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import EntityCategory, UnitOfTime

from .const import LOGGER, EntityKey, MowerOperatingState
from .entity import RobomowEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from .coordinator import RobomowConfigEntry


SENSOR_DESCRIPTIONS = (
    SensorEntityDescription(
        key=EntityKey.STATE,
        translation_key="operating_state",
        icon="mdi:state-machine",
        device_class=SensorDeviceClass.ENUM,
        options=[state.name.lower() for state in MowerOperatingState],
    ),
    SensorEntityDescription(
        key=EntityKey.MESSAGE,
        translation_key="status_message",
        icon="mdi:message-text",
    ),
    SensorEntityDescription(
        key=EntityKey.BATTERY_LEVEL,
        device_class=SensorDeviceClass.BATTERY,
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="%",
    ),
    SensorEntityDescription(
        key=EntityKey.NEXT_DEPARTURE,
        translation_key="next_departure",
        icon="mdi:clock-start",
        entity_category=EntityCategory.DIAGNOSTIC,
        native_unit_of_measurement=UnitOfTime.MINUTES,
    ),
    SensorEntityDescription(
        key=EntityKey.PREVIOUS_DEPARTURE,
        translation_key="previous_departure",
        icon="mdi:history",
        entity_category=EntityCategory.DIAGNOSTIC,
        native_unit_of_measurement=UnitOfTime.MINUTES,
    ),
    SensorEntityDescription(
        key=EntityKey.EXPECTED_DURATION,
        translation_key="expected_duration",
        icon="mdi:timer-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        native_unit_of_measurement=UnitOfTime.MINUTES,
    ),
    SensorEntityDescription(
        key=EntityKey.NO_DEPART_REASON,
        translation_key="no_depart_reason",
        icon="mdi:alert-circle-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: RobomowConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Robomow BLE sensors."""
    LOGGER.debug("Setting up sensor platform for config entry %s", entry.entry_id)
    coordinator = entry.runtime_data

    # Register the processor with the coordinator
    coordinator.async_register_processor(coordinator.processor, SensorEntityDescription)

    # Create sensor entities
    entities = [
        RobomowSensorEntity(coordinator, coordinator.processor, description)
        for description in SENSOR_DESCRIPTIONS
    ]

    # Register for entity additions
    async_add_entities(entities)


class RobomowSensorEntity(RobomowEntity, SensorEntity):  # pyright: ignore[reportIncompatibleVariableOverride]
    """Representation of a Robomow BLE sensor."""

    @property
    def native_value(self) -> Any | None:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Return the current sensor value."""
        if self.entity_key in self.processor.entity_data:
            value = self.processor.entity_data[self.entity_key]
            if self.entity_key.key == EntityKey.STATE and value is not None:
                return value.name.lower()
            return value
        return None
