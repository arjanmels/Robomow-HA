"""Support for Robomow BLE sensors."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.bluetooth.passive_update_processor import (
    PassiveBluetoothDataProcessor,
    PassiveBluetoothDataUpdate,
    PassiveBluetoothEntityKey,
    PassiveBluetoothProcessorEntity,
)
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import SIGNAL_STRENGTH_DECIBELS_MILLIWATT
from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH

from .const import DOMAIN
from .coordinator import (
    RoboMowBLEAdvertisement,
    RoboMowBLEPassiveBluetoothDataProcessor,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from .coordinator import RoboMowBLEConfigEntry

type _SensorValueType = int | None


def advertisement_to_bluetooth_data_update(
    advertisement: RoboMowBLEAdvertisement,
) -> PassiveBluetoothDataUpdate[_SensorValueType]:
    """Convert a RoboMow BLE advertisement to Home Assistant sensor updates."""
    entity_key = PassiveBluetoothEntityKey("signal_strength", advertisement.address)
    device_name = advertisement.name or "Robomow"

    return PassiveBluetoothDataUpdate(
        devices={
            advertisement.address: {
                "connections": {(CONNECTION_BLUETOOTH, advertisement.address)},
                "identifiers": {(DOMAIN, advertisement.address)},
                "name": device_name,
            }
        },
        entity_descriptions={
            entity_key: SensorEntityDescription(
                key="signal_strength",
                device_class=SensorDeviceClass.SIGNAL_STRENGTH,
                native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
                state_class=SensorStateClass.MEASUREMENT,
            )
        },
        entity_data={entity_key: advertisement.rssi},
        entity_names={entity_key: "Signal strength"},
    )


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: RoboMowBLEConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Robomow BLE sensors."""
    coordinator = entry.runtime_data
    processor = PassiveBluetoothDataProcessor(advertisement_to_bluetooth_data_update)
    entry.async_on_unload(
        processor.async_add_entities_listener(
            RoboMowBLESignalSensorEntity, async_add_entities
        )
    )
    entry.async_on_unload(
        coordinator.async_register_processor(processor, SensorEntityDescription)
    )


class RoboMowBLESignalSensorEntity(
    PassiveBluetoothProcessorEntity[
        PassiveBluetoothDataProcessor[_SensorValueType, RoboMowBLEAdvertisement]
    ],
    SensorEntity,
):
    """Representation of a Robomow BLE signal strength sensor."""

    processor: RoboMowBLEPassiveBluetoothDataProcessor[_SensorValueType]

    @property
    def native_value(self) -> _SensorValueType:  # pylint: disable=hass-return-type
        """Return the native value."""
        return self.processor.entity_data.get(self.entity_key)
