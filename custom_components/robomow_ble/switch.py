"""Support for Robomow BLE switches."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.bluetooth.passive_update_processor import (
    PassiveBluetoothDataUpdate,
    PassiveBluetoothEntityKey,
)
from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import callback

from .const import LOGGER, EntityKey
from .entity import RobomowEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from .coordinator import RobomowConfigEntry

SCHEDULE_SWITCH_DESCRIPTION = SwitchEntityDescription(
    key=EntityKey.SCHEDULE_ENABLED,
    translation_key="schedule_enabled",
)

SWITCH_DESCRIPTIONS = (
    SwitchEntityDescription(
        key=EntityKey.ANTI_THEFT_ENABLED,
        translation_key="anti_theft_enabled",
        entity_category=EntityCategory.CONFIG,
    ),
    SwitchEntityDescription(
        key=EntityKey.CHILD_LOCK_ENABLED,
        translation_key="child_lock_enabled",
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
    entities: list[RobomowSwitchEntity] = [
        RobomowScheduleSwitchEntity(
            coordinator,
            coordinator.processor,
            SCHEDULE_SWITCH_DESCRIPTION,
        )
    ]
    entities.extend(
        RobomowSwitchEntity(
            coordinator,
            coordinator.processor,
            description,
        )
        for description in SWITCH_DESCRIPTIONS
    )

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


class RobomowScheduleSwitchEntity(RobomowSwitchEntity):
    """Schedule-enabled switch with schedule detail attributes."""

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()

        schedule_key = PassiveBluetoothEntityKey(
            key=EntityKey.SCHEDULE,
            device_id=self.coordinator.address,
        )
        remove_listener = self.processor.async_add_entity_key_listener(
            self._handle_schedule_update,
            schedule_key,
        )
        self.async_on_remove(remove_listener)

    @callback
    def _handle_schedule_update(
        self, _data: PassiveBluetoothDataUpdate[Any] | None
    ) -> None:
        """Handle schedule update for schedule-enabled switch attributes."""
        self.async_write_ha_state()

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Return schedule details as switch attributes."""
        schedule = self.coordinator.mower.schedule
        if schedule is None:
            return None

        attributes: dict[str, Any] = {
            "start_time": schedule.start_time.strftime("%H:%M:%S"),
            "end_time": schedule.end_time.strftime("%H:%M:%S"),
        }

        weekdays = (
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        )
        for day in range(7):
            day_schedule = schedule.day[day]
            day_name = weekdays[day]
            attributes[f"{day_name}_enabled"] = day_schedule.enabled
            attributes[f"{day_name}_duration"] = day_schedule.duration
            attributes[f"{day_name}_cycles"] = day_schedule.cycles
            attributes[f"{day_name}_zone"] = day_schedule.zone.name.lower()

        return attributes
