"""Data coordinator for Robomow BLE."""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from homeassistant import config_entries
from homeassistant.components.bluetooth import (
    BluetoothScanningMode,
    async_ble_device_from_address,
)
from homeassistant.components.bluetooth.active_update_processor import (
    ActiveBluetoothProcessorCoordinator,
)
from homeassistant.components.bluetooth.passive_update_processor import (
    PassiveBluetoothDataProcessor,
)
from homeassistant.helpers.event import async_track_time_interval

from custom_components.robomow_ble.ble_handler import RoboMowBLEDevice
from custom_components.robomow_ble.const import LOGGER

if TYPE_CHECKING:
    from homeassistant.components.bluetooth import (
        BluetoothServiceInfoBleak,
    )
    from homeassistant.core import HomeAssistant


type RoboMowBLEConfigEntry = config_entries.ConfigEntry[RoboMowBLECoordinator]


@dataclass(slots=True)
class RoboMowBLEAdvertisement:
    """Normalized data from a RoboMow BLE advertisement."""

    address: str
    name: str | None
    rssi: int | None


def process_service_info(
    service_info: BluetoothServiceInfoBleak,
) -> RoboMowBLEAdvertisement:
    """Process bluetooth service info into normalized update data."""
    return RoboMowBLEAdvertisement(
        address=service_info.address,
        name=service_info.name,
        rssi=service_info.rssi,
    )


class RoboMowBLECoordinator(
    ActiveBluetoothProcessorCoordinator[RoboMowBLEAdvertisement]
):
    """Coordinator for passive RoboMow BLE advertisements."""

    def _needs_poll(
        self,
        service_info: BluetoothServiceInfoBleak,
        last_poll: float | None,
    ) -> bool:
        """Return whether the coordinator should poll the device."""
        poll_needed = (
            time.time() - (last_poll or 0) > 1
            and async_ble_device_from_address(
                self.hass, service_info.device.address, connectable=True
            )
            is not None
        )

        LOGGER.debug(
            f"Needs poll for {service_info.name} "
            f"(last poll: {last_poll}): {poll_needed}"
        )
        return poll_needed

    async def _async_poll(self) -> RoboMowBLEAdvertisement | None:
        """Poll the device for updated data."""
        LOGGER.debug("Polling device for updated data")
        try:
            await self._client.update()
        except Exception as e:
            LOGGER.error("Error polling device: %s", e)
        return None

    async def _async_poll_advertisement(
        self, service_info: BluetoothServiceInfoBleak
    ) -> RoboMowBLEAdvertisement:
        LOGGER.debug("Polling device for service info: %s", service_info)
        await self._async_poll()
        return process_service_info(service_info)

    async def _async_poll_timed(self, _now: datetime) -> None:
        """Handle timed polling callback."""
        LOGGER.debug("Timed poll triggered")
        await self._async_poll()

    def __init__(
        self,
        hass: HomeAssistant,
        address: str,
        mainboard_serial: str,
    ) -> None:
        """Initialize the RoboMow BLE active coordinator."""
        LOGGER.debug(
            f"Initializing RoboMowBLECoordinator with address {address}"
            f" and mainboard serial {mainboard_serial}"
        )
        super().__init__(
            hass=hass,
            logger=LOGGER,
            mode=BluetoothScanningMode.PASSIVE,
            address=address,
            update_method=process_service_info,
            needs_poll_method=self._needs_poll,
            poll_method=self._async_poll_advertisement,
        )

        self._mainboard_serial = mainboard_serial
        self._client = RoboMowBLEDevice(hass, address, mainboard_serial)
        self._unsub = async_track_time_interval(
            hass, self._async_poll_timed, timedelta(seconds=30)
        )

    def __del__(self) -> None:
        """Clean up resources when the coordinator is garbage collected."""
        LOGGER.debug("RoboMowBLECoordinator instance is being garbage collected")
        if self._unsub:
            self._unsub()
        if self._client:
            # Schedule the disconnect to run in the event loop
            self.hass.async_create_task(self._client.disconnect())


class RoboMowBLEPassiveBluetoothDataProcessor[T](
    PassiveBluetoothDataProcessor[T, RoboMowBLEAdvertisement]
):
    """Typed passive data processor for RoboMow BLE updates."""

    coordinator: RoboMowBLECoordinator
