"""Support for Robomow BLE switches."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.const import EntityCategory

from .const import LOGGER, EntityKey
from .entity import RobomowEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from .coordinator import RobomowConfigEntry


SWITCH_DESCRIPTIONS = (
    SwitchEntityDescription(
        key=EntityKey.SCHEDULE_ENABLED,
        name="Schedule enabled",
    ),
    SwitchEntityDescription(
        key=EntityKey.ANTI_THEFT_ENABLED,
        name="Anti-theft enabled",
        entity_category=EntityCategory.CONFIG,
    ),
    SwitchEntityDescription(
        key=EntityKey.CHILD_LOCK_ENABLED,
        name="Child lock enabled",
        entity_category=EntityCategory.CONFIG,
    ),
)


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: RobomowConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Robomow BLE switches."""
    LOGGER.debug("Setting up switch platform for config entry %s", entry.entry_id)
    coordinator = entry.runtime_data

    # Register the processor with the coordinator
    coordinator.async_register_processor(coordinator.processor, SwitchEntityDescription)

    # Create switch entities
    entities = [
        RobomowSwitchEntity(coordinator, coordinator.processor, description)
        for description in SWITCH_DESCRIPTIONS
    ]

    async_add_entities(entities)


class RobomowSwitchEntity(RobomowEntity, SwitchEntity):  # pyright: ignore[reportIncompatibleVariableOverride]
    """Representation of a Robomow BLE switch."""

    @property
    def is_on(self) -> bool:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Return True if the switch is on."""
        if self.entity_key in self.processor.entity_data:
            return self.processor.entity_data[self.entity_key]
        return False

    async def async_turn_on(self, **_kwargs: Any) -> None:
        """Turn on the switch."""
        LOGGER.debug(
            "Turning on %s for %s",
            self.entity_description.key,
            self.coordinator.address,
        )
        if self.entity_description.key == EntityKey.SCHEDULE_ENABLED:
            await self.coordinator.mower.async_enable_schedule()
        elif self.entity_description.key == EntityKey.ANTI_THEFT_ENABLED:
            await self.coordinator.mower.async_enable_anti_theft()
        elif self.entity_description.key == EntityKey.CHILD_LOCK_ENABLED:
            await self.coordinator.mower.async_enable_child_lock()
        self.async_write_ha_state()

    async def async_turn_off(self, **_kwargs: Any) -> None:
        """Turn off the switch."""
        LOGGER.debug(
            "Turning off %s for %s",
            self.entity_description.key,
            self.coordinator.address,
        )
        if self.entity_description.key == EntityKey.SCHEDULE_ENABLED:
            await self.coordinator.mower.async_disable_schedule()
        elif self.entity_description.key == EntityKey.ANTI_THEFT_ENABLED:
            await self.coordinator.mower.async_disable_anti_theft()
        elif self.entity_description.key == EntityKey.CHILD_LOCK_ENABLED:
            await self.coordinator.mower.async_disable_child_lock()
        self.async_write_ha_state()
