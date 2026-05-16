"""
Compatibility shim for protocol constants.

Prefer constants from the extracted `robomow_ble` package when available, and
fall back to local definitions while migration is still in progress.
"""

try:
    from robomow_ble.constants import (  # type: ignore[import-untyped]
        AUTH_RESPONSE_LENGTH,
        MAINBOARD_SERIAL_LENGTH,
        MESSAGE_RECEIVE_BYTE,
        MESSAGE_SEND_BYTE,
        MESSAGE_START_BYTE,
        MINIMUM_MESSAGE_LENGTH,
        UUID_CHAR_AUTHENTICATE,
        UUID_CHAR_DATA_IN,
        UUID_CHAR_DATA_OUT,
        MessageType,
        WireSignalType,
    )
except ModuleNotFoundError:
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
