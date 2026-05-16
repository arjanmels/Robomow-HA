"""BLE-layer constants for Robomow — only used inside ble_handler.py."""

from enum import IntEnum

MAINBOARD_SERIAL_LENGTH = 14
AUTH_RESPONSE_LENGTH = 15

MINIMUM_MESSAGE_LENGTH = 4
MESSAGE_START_BYTE = 0xAA
MESSAGE_SEND_BYTE = 0x1F
MESSAGE_RECEIVE_BYTE = 0x1E

UUID_CHAR_AUTHENTICATE = "ff00a502-d020-913c-1234-56d97200a6a6"
UUID_CHAR_DATA_OUT = "ff00a503-d020-913c-1234-56d97200a6a6"
UUID_CHAR_DATA_IN = "ff00a506-d020-913c-1234-56d97200a6a6"


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


class OperationType(IntEnum):
    """Operation types used in command messages."""

    STOP_MOWING = 0x0000
    START_EDGE_MOWING = 0x0001
    START_MOWING = 0x0002
    RETURN_HOME = 0x0003


class MessageTypeMisc(IntEnum):
    """Miscellaneous message types used in packet payloads."""

    INFO = 0x08
    STATE = 0x0B


class EepromParam(IntEnum):
    """EEPROM parameter identifiers."""

    STARTING_POINT_A = 0x000D
    STARTING_POINT_B = 0x000E

    PROGRAM_ENABLED = 0x008C
    ANTI_THEFT_ENABLED = 0x00B9
    CHILD_LOCK_ENABLED = 0x00BC
    WIRE_SIGNAL_TYPE = 0x011F


class WireSignalType(IntEnum):
    """Wire signal types used in EEPROM parameters."""

    TYPE_A = 0x00
    TYPE_B = 0x01
    TYPE_C = 0x02
