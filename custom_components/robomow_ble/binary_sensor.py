"""Support for Robomow BLE binary sensors."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory

from .const import LOGGER, EntityKey
from .entity import RoboMowEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from .coordinator import RoboMowConfigEntry


BINARY_SENSOR_DESCRIPTIONS = (
    BinarySensorEntityDescription(
        key=EntityKey.ANTI_THEFT_ACTIVE,
        name="Anti-theft active",
        icon="mdi:shield-alert",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_visible_default=False,
    ),
    BinarySensorEntityDescription(
        key=EntityKey.MOWER_HOME,
        name="Mower home",
        icon="mdi:home",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_visible_default=False,
    ),
    BinarySensorEntityDescription(
        key=EntityKey.CHARGING_ACTIVE,
        name="Charging active",
        icon="mdi:battery-charging",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_visible_default=False,
    ),
    BinarySensorEntityDescription(
        key=EntityKey.DISABLING_DEVICE_REMOVED,
        name="Disabling device removed",
        icon="mdi:power-plug-off",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_visible_default=False,
    ),
)


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: RoboMowConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Robomow BLE binary sensors."""
    LOGGER.debug(
        "Setting up binary_sensor platform for config entry %s",
        entry.entry_id,
    )
    coordinator = entry.runtime_data

    coordinator.async_register_processor(
        coordinator.processor,
        BinarySensorEntityDescription,
    )

    async_add_entities(
        [
            RoboMowBinarySensorEntity(coordinator, coordinator.processor, description)
            for description in BINARY_SENSOR_DESCRIPTIONS
        ]
    )


class RoboMowBinarySensorEntity(RoboMowEntity, BinarySensorEntity):
    """Representation of a Robomow BLE binary sensor."""

    @property
    def is_on(self) -> bool | None:
        """Return the current binary sensor value."""
        return self.processor.entity_data.get(self.entity_key)
