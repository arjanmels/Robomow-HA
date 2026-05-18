"""Support for Robomow BLE lawn mower entity."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.lawn_mower import (
    LawnMowerEntity,
    LawnMowerEntityEntityDescription,
)
from homeassistant.components.lawn_mower.const import (
    LawnMowerActivity,
    LawnMowerEntityFeature,
)

from .const import LOGGER, EntityKey, MowerOperatingState
from .entity import RobomowEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from robomow_ble.const import Zone

    from .coordinator import RobomowConfigEntry


LAWN_MOWER_DESCRIPTION = LawnMowerEntityEntityDescription(
    key=EntityKey.STATE, name="Mower"
)


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: RobomowConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Robomow BLE lawn mower entity."""
    LOGGER.debug("Setting up lawn_mower platform for config entry %s", entry.entry_id)
    coordinator = entry.runtime_data

    coordinator.async_register_processor(
        coordinator.processor,
        LawnMowerEntityEntityDescription,
    )

    async_add_entities(
        [
            RobomowLawnMowerEntity(
                coordinator,
                coordinator.processor,
                LAWN_MOWER_DESCRIPTION,
            )
        ]
    )


class RobomowLawnMowerEntity(RobomowEntity, LawnMowerEntity):  # pyright: ignore[reportIncompatibleVariableOverride]
    """Representation of a Robomow BLE lawn mower."""

    _attr_supported_features = (
        LawnMowerEntityFeature.START_MOWING
        | LawnMowerEntityFeature.PAUSE
        | LawnMowerEntityFeature.DOCK
    )

    @property
    def activity(self) -> LawnMowerActivity | None:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Return the current mower activity."""
        state = self.processor.entity_data.get(self.entity_key)
        if state in (
            MowerOperatingState.MOWING,
            MowerOperatingState.GOING_TO_START,
            MowerOperatingState.LEARNING_ENTRY_POINT,
            MowerOperatingState.REMOTE_CONTROL,
            MowerOperatingState.BIT,
            MowerOperatingState.WARMING_UP,
        ):
            return LawnMowerActivity.MOWING
        if state in (
            MowerOperatingState.RETURNING_HOME_WARMING_UP,
            MowerOperatingState.RETURNING_HOME_SEARCHING_EDGE,
            MowerOperatingState.RETURNING_HOME_FOLLOWING_EDGE,
        ):
            return LawnMowerActivity.RETURNING
        if state == MowerOperatingState.CHARGING:
            return LawnMowerActivity.DOCKED
        if state == MowerOperatingState.IDLE:
            return LawnMowerActivity.PAUSED
        return LawnMowerActivity.ERROR

    async def async_start_mowing(
        self,
        duration_minutes: int | None = None,
        starting_zone: Zone | None = None,
    ) -> None:
        """Start or resume mowing."""
        if self.activity == LawnMowerActivity.RETURNING:
            LOGGER.debug("Mower is returning, stop first.")
            await self.coordinator.mower.async_stop_mowing()

        await self.coordinator.mower.async_start_mowing(
            duration_minutes,
            starting_zone,
        )

    async def async_pause(self) -> None:
        """Pause mowing."""
        await self.coordinator.mower.async_stop_mowing()

    async def async_dock(self) -> None:
        """Dock mower by returning it home."""
        if self.activity == LawnMowerActivity.MOWING:
            LOGGER.debug("Mower is mowing, stop first.")
            await self.coordinator.mower.async_stop_mowing()

        await self.coordinator.mower.async_return_to_home()
