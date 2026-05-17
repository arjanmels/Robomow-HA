"""Shared constants and enums for the Robomow BLE package."""

from __future__ import annotations

import logging
from enum import IntEnum, StrEnum

LOGGER: logging.Logger = logging.getLogger(__package__)

CONF_DEVICE_TYPE = "device_type"
CONF_MAINBOARD_SERIAL = "mainboard_serial"

MAINBOARD_SERIAL_LENGTH = 14
AUTH_RESPONSE_LENGTH = 15

MINIMUM_MESSAGE_LENGTH = 4
MESSAGE_START_BYTE = 0xAA
MESSAGE_SEND_BYTE = 0x1F
MESSAGE_RECEIVE_BYTE = 0x1E

UUID_SERVICE = "ff00a501-d020-913c-1234-56d97200a6a6"
UUID_CHAR_AUTHENTICATE = "ff00a502-d020-913c-1234-56d97200a6a6"
UUID_CHAR_DATA_OUT = "ff00a503-d020-913c-1234-56d97200a6a6"
UUID_CHAR_DATA_IN = "ff00a506-d020-913c-1234-56d97200a6a6"

UNKNOWN_FIELD_VALUE = 0xFFFF


class MessageType(IntEnum):
    """Basic message types used in packet payloads."""

    ACKNOWLEDGE = 0x04
    CLEAR_USER_MESSAGE = 0x0E
    GET_CONFIG = 0x0F
    COMMAND = 0x15
    MISCELLANEOUS = 0x16
    GET_MESSAGE = 0x1B
    UPDATE_DATE_TIME = 0x1D
    WRITE_EEPROM = 0x1F
    READ_EEPROM = 0x20


class WireSignalType(IntEnum):
    """Wire signal types used in EEPROM parameters."""

    TYPE_A = 0x00
    TYPE_B = 0x01
    TYPE_C = 0x02


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


class EntityKey(StrEnum):
    """Entity keys for all Robomow entities."""

    LAWN_MOWER = "lawn_mower"
    BATTERY_LEVEL = "battery_level"
    FAMILY = "family"
    MODEL = "model"
    SOFTWARE_VERSION = "software_version"
    SOFTWARE_RELEASE = "software_release"
    MAINBOARD_VERSION = "mainboard_version"
    STATE = "state"
    MESSAGE = "message"
    SIGNAL_STRENGTH = "signal_strength"
    START_MOWING = "async_start_mowing"
    STOP_MOWING = "async_stop_mowing"
    RETURN_HOME = "return_home"
    EDGE_MOWING = "edge_mowing"
    PROGRAM_ENABLED = "program_enabled"
    SERVICE_INFO = "service_info"
    NEXT_DEPARTURE = "next_departure"
    PREVIOUS_DEPARTURE = "previous_departure"
    EXPECTED_DURATION = "expected_duration"
    NO_DEPART_REASON = "no_depart_reason"
    ANTI_THEFT_ENABLED = "anti_theft_enabled"
    CHILD_LOCK_ENABLED = "child_lock_enabled"
    ANTI_THEFT_ACTIVE = "anti_theft_active"
    MOWER_HOME = "mower_home"
    CHARGING_ACTIVE = "charging_active"
    DISABLING_DEVICE_REMOVED = "disabling_device_removed"
    WIRE_SIGNAL_TYPE = "wire_signal_type"
    STARTING_POINT_A = "starting_point_a"
    STARTING_POINT_B = "starting_point_b"
