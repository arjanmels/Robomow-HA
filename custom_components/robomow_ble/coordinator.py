"""Data coordinator for Robomow BLE."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bleak.exc import BleakDeviceNotFoundError, BleakError
from homeassistant.components import bluetooth
from homeassistant.components.bluetooth import (
    BluetoothScanningMode,
    async_ble_device_from_address,
)
from homeassistant.components.bluetooth.passive_update_processor import (
    PassiveBluetoothDataProcessor,
    PassiveBluetoothDataUpdate,
    PassiveBluetoothEntityKey,
    PassiveBluetoothProcessorCoordinator,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import ConfigEntryError
from homeassistant.helpers import device_registry as dr

from robomow_ble import EntityKey, RobomowDevice, RobomowUpdate

from .const import CONF_MAINBOARD_SERIAL, DOMAIN, LOGGER, MANUFACTURER

if TYPE_CHECKING:
    from homeassistant.components.bluetooth import (
        BluetoothServiceInfoBleak,
    )
    from homeassistant.core import HomeAssistant


type RobomowConfigEntry = ConfigEntry[RobomowCoordinator]


class RobomowCoordinator(PassiveBluetoothProcessorCoordinator[RobomowUpdate]):
    """Coordinator for Robomow BLE passive polling."""

    _DEVICE_INFO_UPDATE_KEYS = frozenset(
        {
            EntityKey.MODEL,
            EntityKey.FAMILY,
            EntityKey.SOFTWARE_VERSION,
            EntityKey.SOFTWARE_RELEASE,
            EntityKey.MAINBOARD_VERSION,
        }
    )

    def __init__(
        self,
        hass: HomeAssistant,
        entry: RobomowConfigEntry,
    ) -> None:
        """Initialize the coordinator."""
        address = entry.unique_id
        if address is None:
            raise ConfigEntryError(
                translation_domain=DOMAIN, translation_key="no_unique_address"
            )

        mainboard_serial = entry.data.get(CONF_MAINBOARD_SERIAL)
        if mainboard_serial is None:
            raise ConfigEntryError(
                translation_domain=DOMAIN, translation_key="no_mainboard_serial"
            )

        """Initialize the Robomow BLE coordinator."""
        LOGGER.debug(
            "Initializing RobomowBLECoordinator with address %s "
            "and mainboard serial %s",
            address,
            mainboard_serial,
        )

        super().__init__(
            hass=hass,
            logger=LOGGER,
            address=address,
            mode=BluetoothScanningMode.ACTIVE,
            update_method=self._update_from_service_info,
            connectable=True,
        )

        self._mower = RobomowDevice(
            address,
            mainboard_serial,
            self.async_set_updated_data,
        )
        self._processor: PassiveBluetoothDataProcessor[Any, RobomowUpdate] | None = None
        self._entry = entry

    def _update_device_info(self) -> None:
        """Push latest mower metadata into the device registry."""
        device_registry = dr.async_get(self.hass)
        device = device_registry.async_get_device(identifiers={(DOMAIN, self.address)})
        if device is None:
            return

        device_registry.async_update_device(
            device.id,
            model=f"Robomow {self.mower.model.name}",
            model_id=f"{self.mower.model}",
            manufacturer=MANUFACTURER,
            serial_number=self._mower.mainboard_serial,
            hw_version=(
                f"{self.mower.mainboard_version}"
                if self.mower.mainboard_version is not None
                else "Unknown"
            ),
            sw_version=(
                (
                    f"{self.mower.software_version} "
                    f"({
                        self.mower.software_release
                        if self.mower.software_release is not None
                        else 'Unknown'
                    })"
                )
                if self.mower.software_version is not None
                else "Unknown"
            ),
        )

    def _get_entity_data(
        self, update: RobomowUpdate
    ) -> PassiveBluetoothDataUpdate[Any]:
        """Map updates to entity-keyed processor data."""
        if update.key in self._DEVICE_INFO_UPDATE_KEYS:
            self._update_device_info()

        return PassiveBluetoothDataUpdate(
            entity_data={
                PassiveBluetoothEntityKey(
                    key=update.key, device_id=self.address
                ): update.value
            }
        )

    @property
    def processor(self) -> PassiveBluetoothDataProcessor[Any, RobomowUpdate]:
        """Return the shared entity processor."""
        if self._processor is None:
            self._processor = PassiveBluetoothDataProcessor(
                update_method=self._get_entity_data,
            )
        return self._processor

    async def _async_connect_on_advertisement(self) -> None:
        """Connect to the mower and clear cached advertisement history."""
        device = async_ble_device_from_address(
            self.hass, self.address, connectable=True
        )
        if device is None:
            msg = f"Device with address {self.address} not found"
            raise BleakDeviceNotFoundError(msg)

        try:
            await self._mower.async_connect(device)
            bluetooth.async_clear_advertisement_history(self.hass, self.address)
        except (BleakError, OSError) as err:
            LOGGER.error(
                "Error connecting after advertisement for %s: %s",
                self.address,
                err,
            )

    def _update_from_service_info(
        self,
        service_info: BluetoothServiceInfoBleak,
    ) -> RobomowUpdate:
        """Process the latest data and return the device."""
        LOGGER.debug("Processing update from device %s", self.address)

        self.hass.async_create_task(self._async_connect_on_advertisement())

        try:
            # Update device data from service info
            self._mower.update_from_rssi(service_info.rssi)
        except (BleakError, OSError) as err:
            LOGGER.error("Error processing device update: %s", err)
        return RobomowUpdate(EntityKey.SERVICE_INFO, service_info)

    @property
    def mower(self) -> RobomowDevice:
        """Return the BLE device."""
        return self._mower

    async def async_shutdown(self) -> None:
        """Disconnect from the BLE client (called when config entry is unloaded)."""
        LOGGER.debug("Shutting down coordinator for %s", self.address)
        await self._mower.async_disconnect()
