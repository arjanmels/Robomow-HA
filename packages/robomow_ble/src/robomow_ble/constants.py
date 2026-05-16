"""Protocol constants and enums for RoboMow BLE packets."""

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


class WireSignalType(IntEnum):
    """Wire signal types used in EEPROM parameters."""

    TYPE_A = 0x00
    TYPE_B = 0x01
    TYPE_C = 0x02
