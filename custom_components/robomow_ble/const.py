#!/usr/bin/env python3
"""Constants for Robomow."""

import logging
from enum import IntEnum, StrEnum

LOGGER: logging.Logger = logging.getLogger(__package__)

DOMAIN = "robomow_ble"
MANUFACTURER = "RoboMow"

CONF_DEVICE_TYPE = "device_type"
CONF_MAINBOARD_SERIAL = "mainboard_serial"

UUID_SERVICE = "ff00a501-d020-913c-1234-56d97200a6a6"

UNKNOWN_FIELD_VALUE = 0xFFFF


class MowerFamily(IntEnum):
    """RoboMow mower types."""

    Unknown = -1
    RS = 1
    RC = 2
    RX = 3
    RK = 4
    RT = 5


class MowerModel(IntEnum):
    """RoboMow mower models."""

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
    """Entity keys for all RoboMow entities."""

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
    START_MOWING = "start_mowing"
    STOP_MOWING = "stop_mowing"
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
