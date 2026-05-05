"""Support for Robomow BLE buttons."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription

from .const import DOMAIN, LOGGER
from .coordinator import RoboMowBLECoordinatorEntity

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from .ble_handler import RoboMowBLEDevice
    from .coordinator import RoboMowBLEConfigEntry, RoboMowBLECoordinator


type _ButtonAction = Callable[[RoboMowBLEDevice], Awaitable[bool]]


@dataclass(frozen=True, kw_only=True)
class RoboMowBLEButtonDescription(ButtonEntityDescription):
    """Description of a Robomow BLE button."""

    action: _ButtonAction


BUTTONS: tuple[RoboMowBLEButtonDescription, ...] = (
    RoboMowBLEButtonDescription(
        key="start_mowing",
        name="Start mowing",
        icon="mdi:robot-mower",
        action=lambda device: device.start_mowing(),
    ),
    RoboMowBLEButtonDescription(
        key="stop_mowing",
        name="Stop mowing",
        icon="mdi:stop",
        action=lambda device: device.stop_mowing(),
    ),
    RoboMowBLEButtonDescription(
        key="return_home",
        name="Return home",
        icon="mdi:home-map-marker",
        action=lambda device: device.return_to_home(),
    ),
    RoboMowBLEButtonDescription(
        key="edge_mowing",
        name="Edge mowing",
        icon="mdi:border-all",
        action=lambda device: device.start_mowing_edge(),
    ),
)


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: RoboMowBLEConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Robomow BLE buttons."""
    LOGGER.debug("Setting up button platform for config entry %s", entry.entry_id)
    coordinator = entry.runtime_data
    async_add_entities(
        RoboMowBLEButtonEntity(coordinator, description) for description in BUTTONS
    )


class RoboMowBLEButtonEntity(RoboMowBLECoordinatorEntity, ButtonEntity):
    """Representation of a Robomow BLE command button."""

    _attr_has_entity_name = True

    entity_description: RoboMowBLEButtonDescription

    def __init__(
        self,
        coordinator: RoboMowBLECoordinator,
        description: RoboMowBLEButtonDescription,
    ) -> None:
        """Initialize the button."""
        self._init_coordinator_entity(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{DOMAIN}_{coordinator.address}_{description.key}"

    async def async_press(self) -> None:
        """Run the command associated with this button."""
        await self.entity_description.action(self.coordinator.device)
