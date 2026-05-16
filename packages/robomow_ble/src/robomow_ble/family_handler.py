"""Family-specific protocol handler interfaces for RoboMow BLE devices."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime

    from .constants import WireSignalType


class RoboMowFamilyHandler(ABC):
    """Base interface for family-specific RoboMow protocol behavior."""

    @abstractmethod
    async def initialize_state(self) -> None:
        """Initialize family-specific state after connection."""

    @abstractmethod
    async def poll_status(self) -> None:
        """Poll family-specific status while connected."""

    @abstractmethod
    async def enable_program(self) -> None:
        """Enable mower program."""

    @abstractmethod
    async def disable_program(self) -> None:
        """Disable mower program."""

    @abstractmethod
    async def enable_anti_theft(self) -> None:
        """Enable anti-theft mode."""

    @abstractmethod
    async def disable_anti_theft(self) -> None:
        """Disable anti-theft mode."""

    @abstractmethod
    async def enable_child_lock(self) -> None:
        """Enable child lock mode."""

    @abstractmethod
    async def disable_child_lock(self) -> None:
        """Disable child lock mode."""

    @abstractmethod
    async def set_wire_signal_type(self, wire_signal_type: WireSignalType) -> None:
        """Set wire signal type."""

    @abstractmethod
    async def set_starting_point_a(self, value: int) -> None:
        """Set starting point A."""

    @abstractmethod
    async def set_starting_point_b(self, value: int) -> None:
        """Set starting point B."""

    @abstractmethod
    async def start_mowing(
        self,
        duration_minutes: int | None = None,
        starting_zone: int | None = None,
    ) -> None:
        """Start mowing."""

    @abstractmethod
    async def start_mowing_edge(self) -> None:
        """Start edge mowing."""

    @abstractmethod
    async def stop_mowing(self) -> None:
        """Stop mowing."""

    @abstractmethod
    async def return_to_home(self) -> None:
        """Return mower to home."""

    @abstractmethod
    async def update_date_time(self, timestamp: datetime | None = None) -> bool:
        """Update device date/time."""

    @abstractmethod
    def handle_get_message(self, payload: bytes) -> None:
        """Handle GET_MESSAGE payload."""

    @abstractmethod
    def handle_read_eeprom_response(self, request: object, response: object) -> None:
        """Handle READ_EEPROM response payload."""

    @abstractmethod
    def handle_miscellaneous_response(self, request: object, response: object) -> None:
        """Handle MISCELLANEOUS response payload."""
