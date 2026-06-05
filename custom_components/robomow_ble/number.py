"""Support for Robomow BLE number entities."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.number import NumberEntity, NumberEntityDescription
from homeassistant.const import EntityCategory

from .const import LOGGER, EntityKey
from .entity import RobomowEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from .coordinator import RobomowConfigEntry


NUMBER_DESCRIPTIONS = (
    NumberEntityDescription(
        key=EntityKey.STARTING_POINT_A,
        translation_key="starting_point_a",
        icon="mdi:map-marker-path",
        entity_category=EntityCategory.CONFIG,
        native_unit_of_measurement="m",
        native_min_value=0,
        native_max_value=1000,
        native_step=0.1,
        entity_registry_enabled_default=False,
        entity_registry_visible_default=False,
    ),
    NumberEntityDescription(
        key=EntityKey.STARTING_POINT_B,
        translation_key="starting_point_b",
        icon="mdi:map-marker-path",
        entity_category=EntityCategory.CONFIG,
        native_unit_of_measurement="m",
        native_min_value=0,
        native_max_value=1000,
        native_step=0.1,
        entity_registry_enabled_default=False,
        entity_registry_visible_default=False,
    ),
)


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: RobomowConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Robomow BLE number entities."""
    LOGGER.debug("Setting up number platform for config entry %s", entry.entry_id)
    coordinator = entry.runtime_data

    coordinator.async_register_processor(coordinator.processor, NumberEntityDescription)

    async_add_entities(
        [
            RobomowNumberEntity(coordinator, coordinator.processor, description)
            for description in NUMBER_DESCRIPTIONS
        ]
    )


class RobomowNumberEntity(RobomowEntity, NumberEntity):  # pyright: ignore[reportIncompatibleVariableOverride]
    """Representation of a Robomow BLE number entity."""

    _attr_suggested_display_precision = 1

    @property
    def native_value(self) -> float | None:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Return the current number value."""
        value = self.processor.entity_data.get(self.entity_key)
        if value is None:
            return None
        return float(value) / 100

    async def async_set_native_value(self, value: float) -> None:
        """Set a new number value."""
        int_value = round(value * 100)

        if self.entity_description.key == EntityKey.STARTING_POINT_A:
            await self.coordinator.mower.async_set_starting_point_a(int_value)
        elif self.entity_description.key == EntityKey.STARTING_POINT_B:
            await self.coordinator.mower.async_set_starting_point_b(int_value)
