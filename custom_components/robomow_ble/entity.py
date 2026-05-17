"""Provides the Robomow BLE entity base class."""

from typing import TYPE_CHECKING, Any

from homeassistant.components.bluetooth.passive_update_processor import (
    PassiveBluetoothDataProcessor,
    PassiveBluetoothDataUpdate,
    PassiveBluetoothEntityKey,
)
from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity, EntityDescription

from custom_components.robomow_ble.const import DOMAIN

if TYPE_CHECKING:
    from custom_components.robomow_ble.coordinator import RobomowCoordinator


class RobomowEntity(Entity):
    """Base class for Robomow BLE entities."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        coordinator: RobomowCoordinator,
        processor: PassiveBluetoothDataProcessor[Any, Any],
        description: EntityDescription,
    ) -> None:  # type: ignore[name-defined]
        """Initialize the Robomow BLE entity."""
        self.coordinator = coordinator
        self.processor = processor
        self.entity_key = PassiveBluetoothEntityKey(
            key=description.key, device_id=self.coordinator.address
        )
        self.entity_description = description

        self._attr_unique_id = f"{DOMAIN}_{coordinator.address}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.address)},
            suggested_area="Garden",
        )

    @callback
    def _handle_update(self, _data: PassiveBluetoothDataUpdate[Any] | None) -> None:
        """Handle data update."""
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()
        # Listen to processor updates for this entity key
        self.async_on_remove(
            self.processor.async_add_entity_key_listener(
                self._handle_update, self.entity_key
            )
        )

    @property
    def available(self) -> bool:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Return True if the device is available."""
        return self.coordinator.available and self.coordinator.mower.is_connected()
