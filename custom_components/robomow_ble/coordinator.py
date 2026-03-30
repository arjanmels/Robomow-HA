"""Data coordinator for Robomow BLE."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from homeassistant.components.bluetooth.passive_update_processor import (
    PassiveBluetoothDataProcessor,
    PassiveBluetoothProcessorCoordinator,
)
from homeassistant.config_entries import ConfigEntry

if TYPE_CHECKING:
    from collections.abc import Callable
    from logging import Logger

    from homeassistant.components.bluetooth import (
        BluetoothScanningMode,
        BluetoothServiceInfoBleak,
    )
    from homeassistant.core import HomeAssistant

type RoboMowBLEConfigEntry = ConfigEntry[RoboMowBLECoordinator]


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
    PassiveBluetoothProcessorCoordinator[RoboMowBLEAdvertisement]
):
    """Coordinator for passive RoboMow BLE advertisements."""

    def __init__(
        self,
        hass: HomeAssistant,
        logger: Logger,
        address: str,
        mode: BluetoothScanningMode,
    ) -> None:
        """Initialize the RoboMow BLE passive coordinator."""
        update_method: Callable[
            [BluetoothServiceInfoBleak], RoboMowBLEAdvertisement
        ] = process_service_info
        super().__init__(hass, logger, address, mode, update_method)


class RoboMowBLEPassiveBluetoothDataProcessor[T](
    PassiveBluetoothDataProcessor[T, RoboMowBLEAdvertisement]
):
    """Typed passive data processor for RoboMow BLE updates."""

    coordinator: RoboMowBLECoordinator
