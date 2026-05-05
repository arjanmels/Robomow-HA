"""Data coordinator for Robomow BLE."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from bleak.exc import BleakError
from homeassistant import config_entries
from homeassistant.components import bluetooth
from homeassistant.components.bluetooth import (
    BluetoothChange,
    BluetoothScanningMode,
)
from homeassistant.components.bluetooth.active_update_processor import (
    ActiveBluetoothProcessorCoordinator,
)
from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import async_track_time_interval

from custom_components.robomow_ble.ble_handler import RoboMowBLEDevice
from custom_components.robomow_ble.const import DOMAIN, LOGGER

if TYPE_CHECKING:
    from collections.abc import Callable

    from homeassistant.components.bluetooth import (
        BluetoothServiceInfoBleak,
    )
    from homeassistant.core import HomeAssistant


type RoboMowBLEConfigEntry = config_entries.ConfigEntry[RoboMowBLECoordinator]


POLL_INTERVAL_SECONDS = 30
POLL_INTERVAL = timedelta(seconds=POLL_INTERVAL_SECONDS)


def _ignore_service_info(_service_info: BluetoothServiceInfoBleak) -> None:
    """Ignore advertisement payloads; this integration polls on a timer."""
    return


class RoboMowBLECoordinator(ActiveBluetoothProcessorCoordinator[None]):
    """Coordinator for timed Robomow BLE polling."""

    def _needs_poll(
        self,
        _service_info: BluetoothServiceInfoBleak,
        _last_poll: float | None,
    ) -> bool:
        """Enable advertisement-driven polling."""
        LOGGER.debug(
            "Polling always needed: need to restore connection if device is advertising"
        )
        return True

    async def _async_poll_advertisement(
        self, _service_info: BluetoothServiceInfoBleak
    ) -> None:
        """Poll the device on every advertisement."""
        LOGGER.debug("Starting poll of device %s", self.address)
        try:
            await self._client.connect()
            bluetooth.async_clear_advertisement_history(self.hass, self.address)
        except BleakError as e:
            LOGGER.error("Error polling device: %s", e)

    def _async_handle_bluetooth_event(
        self,
        _service_info: BluetoothServiceInfoBleak,
        _change: BluetoothChange,
    ) -> None:
        """Handle incoming Bluetooth events."""
        LOGGER.debug(
            "Received Bluetooth event for device %s: change=%s, service_info=%s",
            self.address,
            _change,
            _service_info,
        )
        super()._async_handle_bluetooth_event(_service_info, _change)

    def __init__(
        self,
        hass: HomeAssistant,
        address: str,
        mainboard_serial: str,
    ) -> None:
        """Initialize the RoboMow BLE active coordinator."""
        LOGGER.debug(
            (
                "Initializing RoboMowBLECoordinator with address %s "
                "and mainboard serial %s"
            ),
            address,
            mainboard_serial,
        )
        super().__init__(
            hass=hass,
            logger=LOGGER,
            mode=BluetoothScanningMode.ACTIVE,
            address=address,
            poll_method=self._async_poll_advertisement,
            needs_poll_method=self._needs_poll,
            update_method=_ignore_service_info,
        )

        self._client = RoboMowBLEDevice(hass, address, mainboard_serial)

    @property
    def device(self) -> RoboMowBLEDevice:
        """Return the BLE device."""
        return self._client

    async def async_shutdown(self) -> None:
        """Stop polling and disconnect the BLE client."""
        LOGGER.debug("Shutting down coordinator for %s", self.address)

        await self._client.disconnect()


class RoboMowBLECoordinatorEntity(Entity):
    """Base mixin for entities backed by a Robomow BLE coordinator."""

    coordinator: RoboMowBLECoordinator
    _remove_state_listener: Callable[[], None] | None

    def _init_coordinator_entity(self, coordinator: RoboMowBLECoordinator) -> None:
        """Initialize shared coordinator-backed entity state."""
        self.coordinator = coordinator
        self._remove_state_listener = None

    async def async_added_to_hass(self) -> None:
        """Register for BLE state updates when added to Home Assistant."""
        await super().async_added_to_hass()
        self._remove_state_listener = self.coordinator.device.add_state_listener(
            self._handle_device_state_update
        )

    async def async_will_remove_from_hass(self) -> None:
        """Unregister BLE state updates when removed from Home Assistant."""
        if self._remove_state_listener is not None:
            self._remove_state_listener()
            self._remove_state_listener = None
        await super().async_will_remove_from_hass()

    def _handle_device_state_update(self) -> None:
        """Handle BLE state updates from the underlying device."""
        if self.hass is None:
            return
        self.hass.loop.call_soon_threadsafe(self.async_write_ha_state)

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information."""
        return {
            "connections": {(CONNECTION_BLUETOOTH, self.coordinator.address)},
            "identifiers": {(DOMAIN, self.coordinator.address)},
            "name": f"Robomow {self.coordinator.address.replace(':', '').upper()[-4:]}",
            "manufacturer": "RoboMow",
            "hw_version": self.coordinator.device.mainboard_version,
            "sw_version": self.coordinator.device.software_release,
            "serial_number": self.coordinator.device.mainboard_serial,
            "model": f"RoboMow {self.coordinator.device.family}",
        }

    @property
    def available(self) -> bool:
        """Return True if the device is connected."""
        return self.coordinator.device.is_connected()
