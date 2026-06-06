"""Constants for Robomow."""

import logging
from enum import IntEnum, StrEnum

from robomow_ble_lib import EntityKey

__all__ = ["EntityKey", "MowerFamily", "MowerModel", "MowerOperatingState"]

LOGGER: logging.Logger = logging.getLogger(__package__)

DOMAIN = "robomow_ble"
MANUFACTURER = "Robomow"

CONF_DEVICE_TYPE = "device_type"
CONF_MAINBOARD_SERIAL = "mainboard_serial"

UUID_SERVICE = "ff00a501-d020-913c-1234-56d97200a6a6"

UNKNOWN_FIELD_VALUE = 0xFFFF


class MowerFamily(IntEnum):
    """Robomow mower types."""

    Unknown = -1
    RS = 1
    RC = 2
    RX = 3
    RK = 4
    RT = 5


class MowerModel(IntEnum):
    """Robomow mower models."""

    Unknown = -1
    RT300 = 5
    RT500 = 6
    RT700 = 7


class MowerOperatingState(StrEnum):
    """Human-readable Robomow operating states."""

    WARMING_UP = "Warming up"
    MOWING = "Mowing"
    EDGE_MOWING = "Edge Mowing"
    RETURNING_HOME_FOLLOWING_EDGE = "Following edge home"
    RETURNING_HOME_WARMING_UP = "Warming up to return home"
    RETURNING_HOME_SEARCHING_EDGE = "Searching edge"

    GOING_TO_START = "Going to starting point"
    LEARNING_ENTRY_POINT = "Learning entry point"
    IDLE = "Idle"
    CHARGING = "Charging"
    AUTOMATIC = "Automatic"
    REMOTE_CONTROL = "Remote control"
    BIT = "Bit"
