"""Support for Robomow BLE select entities."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.const import EntityCategory
from robomow_ble_lib import WireSignalType

from .const import LOGGER, EntityKey
from .entity import RobomowEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from .coordinator import RobomowConfigEntry


SELECT_DESCRIPTIONS = (
    SelectEntityDescription(
        key=EntityKey.WIRE_SIGNAL_TYPE,
        translation_key="wire_signal_type",
        icon="mdi:sine-wave",
        entity_category=EntityCategory.CONFIG,
        options=[wire_signal_type.name.lower() for wire_signal_type in WireSignalType],
        entity_registry_enabled_default=False,
        entity_registry_visible_default=False,
    ),
)


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: RobomowConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Robomow BLE select entities."""
    LOGGER.debug("Setting up select platform for config entry %s", entry.entry_id)
    coordinator = entry.runtime_data

    coordinator.async_register_processor(coordinator.processor, SelectEntityDescription)

    async_add_entities(
        [
            RobomowSelectEntity(coordinator, coordinator.processor, description)
            for description in SELECT_DESCRIPTIONS
        ]
    )


class RobomowSelectEntity(RobomowEntity, SelectEntity):  # pyright: ignore[reportIncompatibleVariableOverride]
    """Representation of a Robomow BLE select entity."""

    @property
    def current_option(self) -> str | None:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Return the currently selected option."""
        value = self.processor.entity_data.get(self.entity_key)
        if value is None:
            return None

        try:
            return WireSignalType(value).name.lower()
        except ValueError:
            return None

    async def async_select_option(self, option: str) -> None:
        """Change selected option."""
        wire_signal_type = WireSignalType[option.upper()]
        await self.coordinator.mower.async_set_wire_signal_type(wire_signal_type)
