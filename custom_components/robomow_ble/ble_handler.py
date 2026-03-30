"""BLE device data structures for the Robomow integration."""

from typing import TYPE_CHECKING

from bluetooth_data_tools import short_address
from bluetooth_sensor_state_data import BluetoothData

from .const import LOGGER

if TYPE_CHECKING:
    from homeassistant.components.bluetooth import (
        BluetoothServiceInfoBleak as BluetoothServiceInfo,
    )


class RoboMowBLEDeviceData(BluetoothData):
    """Data about a Robomow BLE device."""

    def _start_update(self, service_info: BluetoothServiceInfo) -> None:
        """Update from BLE advertisement data."""

        manufacturer_data = service_info.manufacturer_data
        _service_uuids = service_info.service_uuids
        local_name = service_info.name
        address = service_info.address
        self.set_device_manufacturer("Robomow")

        if local_name.startswith("Robomow_"):
            self.set_device_name(service_info.name[8:].replace("_", " "))

        if local_name.startswith("RM"):
            self.set_device_name(service_info.name[2:].replace("_", " "))
        self.set_precision(2)

        for mfr_id in manufacturer_data:
            if mfr_id == 2409:
                self.set_device_type("RX")
                self.set_device_name(f"RX{short_address(address)}")
                return

    @property
    def device_type(self) -> str | None:
        """Return the device type."""
        primary_device_id = self.primary_device_id
        if device_type := self._device_id_to_type.get(primary_device_id):
            return device_type.partition("-")[0]
        return None

