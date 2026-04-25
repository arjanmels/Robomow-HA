#!/usr/bin/env python3
"""Constants for Robomow."""

import logging
from enum import IntEnum, auto

LOGGER: logging.Logger = logging.getLogger(__package__)

DOMAIN = "robomow_ble"

CONF_DEVICE_TYPE = "device_type"
CONF_MAINBOARD_SERIAL = "mainboard_serial"

UUID_SERVICE = "ff00a501-d020-913c-1234-56d97200a6a6"
UUID_CHAR_AUTHENTICATE = "ff00a502-d020-913c-1234-56d97200a6a6"
UUID_CHAR_DATA_OUT = "ff00a503-d020-913c-1234-56d97200a6a6"
UUID_CHAR_DATA_IN = "ff00a506-d020-913c-1234-56d97200a6a6"

MAINBOARD_SERIAL_LENGTH = 14
AUTH_RESPONSE_LENGTH = 15

MINIMUM_MESSAGE_LENGTH = 4
MESSAGE_START_BYTE = 0xAA
MESSAGE_SEND_BYTE = 0x1F
MESSAGE_RECEIVE_BYTE = 0x1E


class MessageType(IntEnum):
    """Basic message types used in packet payloads."""

    ACKNOWLEDGE = 0x04
    GET_CONFIG = 0x0F
    MISCELLANEOUS = 0x16
    GET_STATUS = 0x1B
    UPDATE_DATE_TIME = 0x1D
    WRITE_EEPROM = 0x1F
    READ_EEPROM = 0x20


class MessageTypeMisc(IntEnum):
    """Miscellaneous message types used in packet payloads."""

    ROBOT_STATE = 0x08
    CLEAR_USER_MESSAGE = 0x0E


class EepromParam(IntEnum):
    """EEPROM parameter identifiers."""

    PROGRAM_ENABLED = 0x8C
    CHILD_LOCK = 0xBC


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

    RT300 = auto()
    RT500 = auto()
    RT700 = auto()
    RK1000 = auto()
    RK2000 = auto()
    RK3000 = auto()
    RK4000 = auto()
    RKS1000 = auto()
    RKS1200 = auto()
    RKS1500 = auto()
    RKS1700 = auto()
    RKS800 = auto()
