"""Support for Robomow BLE lawn mower entity."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.bluetooth.passive_update_processor import (
    PassiveBluetoothDataUpdate,
    PassiveBluetoothEntityKey,
)
from homeassistant.components.lawn_mower import (
    LawnMowerEntity,
    LawnMowerEntityEntityDescription,
)
from homeassistant.components.lawn_mower.const import (
    LawnMowerActivity,
    LawnMowerEntityFeature,
)
from homeassistant.core import callback
from robomow_ble_lib import EntityKey, MowerOperatingState

from .const import LOGGER
from .entity import RobomowEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
    from robomow_ble_lib import Zone

    from .coordinator import RobomowConfigEntry


LAWN_MOWER_DESCRIPTION = LawnMowerEntityEntityDescription(
    key=EntityKey.STATE, translation_key="mower"
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

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()

        operations_key = PassiveBluetoothEntityKey(
            key=EntityKey.LAST_OPERATIONS,
            device_id=self.coordinator.address,
        )
        remove_listener = self.processor.async_add_entity_key_listener(
            self._handle_last_operations_update,
            operations_key,
        )
        self.async_on_remove(remove_listener)

    @callback
    def _handle_last_operations_update(
        self, _data: PassiveBluetoothDataUpdate[Any] | None
    ) -> None:
        """Handle operation history updates for entity attributes."""
        self.async_write_ha_state()

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

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Expose last operations history as lawn mower attributes."""
        operations = self.coordinator.mower.last_operations

        operation_attributes: list[dict[str, Any]] = []
        for operation in operations:
            operation_data: dict[str, Any] = {
                "start_time": operation.start_time.isoformat(),
                "duration": operation.duration,
                "zone": operation.zone.name.lower(),
                "error_title": operation.error.title,
                "error_number": operation.error.number,
            }
            if operation.error.text is not None:
                operation_data["error_text"] = operation.error.text
            operation_attributes.append(operation_data)

        return {"last_operations": operation_attributes}

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
