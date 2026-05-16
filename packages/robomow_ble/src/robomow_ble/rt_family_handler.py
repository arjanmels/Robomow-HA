"""RT-family protocol handler for RoboMow BLE."""

# ruff: noqa: SLF001

from __future__ import annotations

import logging
import struct
from datetime import datetime
from typing import Any

from .constants import MessageType, WireSignalType
from .family_handler import RoboMowFamilyHandler
from .messages import MessageRK, MessageRT
from .rt_family_types import EepromParam, MessageTypeMisc, OperationType

LOGGER = logging.getLogger(__name__)
UNKNOWN_FIELD_VALUE = 0xFFFF

GET_STATUS_PAYLOAD_SIZE = 7
READ_EEPROM_PAYLOAD_SIZE = 4
INFO_PAYLOAD_SIZE = 5
MISC_TYPE_SIZE = 2
ROBOT_STATE_PAYLOAD_MIN_SIZE = 17
MESSAGE_TYPE_STOP_ID_MASK = 0x2


class RoboMowRtFamilyHandler(RoboMowFamilyHandler):
    """RT-family RoboMow BLE protocol behavior."""

    def __init__(self, device: Any) -> None:
        """Initialize RT family handler with a backing device."""
        self._device = device

    async def initialize_state(self) -> None:
        """Initialize RT-family state after connection."""
        await self._device._send_msg(MessageType.GET_MESSAGE)
        await self._device._send_misc_msg(MessageTypeMisc.INFO)
        await self._device._read_eeprom_param(
            EepromParam.CHILD_LOCK_ENABLED,
            EepromParam.ANTI_THEFT_ENABLED,
            EepromParam.PROGRAM_ENABLED,
            EepromParam.WIRE_SIGNAL_TYPE,
            EepromParam.STARTING_POINT_A,
            EepromParam.STARTING_POINT_B,
        )

    async def poll_status(self) -> None:
        """Poll RT-family status while connected."""
        await self._device._send_msg(MessageType.GET_MESSAGE)
        await self._device._send_misc_msg(MessageTypeMisc.STATE)
        await self._device._read_eeprom_param(
            EepromParam.CHILD_LOCK_ENABLED,
            EepromParam.ANTI_THEFT_ENABLED,
        )

    async def enable_program(self) -> None:
        """Enable the mower program."""
        await self._device._write_eeprom_param(EepromParam.PROGRAM_ENABLED, 1)
        await self._device._send_misc_msg(MessageTypeMisc.STATE)

    async def disable_program(self) -> None:
        """Disable the mower program."""
        await self._device._write_eeprom_param(EepromParam.PROGRAM_ENABLED, 0)
        await self._device._send_misc_msg(MessageTypeMisc.STATE)

    async def enable_anti_theft(self) -> None:
        """Enable anti-theft mode."""
        await self._device._write_eeprom_param(EepromParam.ANTI_THEFT_ENABLED, 1)
        await self._device._send_misc_msg(MessageTypeMisc.STATE)

    async def disable_anti_theft(self) -> None:
        """Disable anti-theft mode."""
        await self._device._write_eeprom_param(EepromParam.ANTI_THEFT_ENABLED, 0)
        await self._device._send_misc_msg(MessageTypeMisc.STATE)

    async def enable_child_lock(self) -> None:
        """Enable child lock mode."""
        await self._device._write_eeprom_param(EepromParam.CHILD_LOCK_ENABLED, 1)
        await self._device._send_misc_msg(MessageTypeMisc.STATE)
        await self._device._read_eeprom_param(EepromParam.CHILD_LOCK_ENABLED)

    async def disable_child_lock(self) -> None:
        """Disable child lock mode."""
        await self._device._write_eeprom_param(EepromParam.CHILD_LOCK_ENABLED, 0)
        await self._device._send_misc_msg(MessageTypeMisc.STATE)
        await self._device._read_eeprom_param(EepromParam.CHILD_LOCK_ENABLED)

    async def set_wire_signal_type(self, wire_signal_type: WireSignalType) -> None:
        """Set wire signal type and refresh it from EEPROM."""
        await self._device._write_eeprom_param(
            EepromParam.WIRE_SIGNAL_TYPE, int(wire_signal_type)
        )
        await self._device._read_eeprom_param(EepromParam.WIRE_SIGNAL_TYPE)

    async def set_starting_point_a(self, value: int) -> None:
        """Set starting point A and refresh it from EEPROM."""
        await self._device._write_eeprom_param(EepromParam.STARTING_POINT_A, value)
        await self._device._read_eeprom_param(EepromParam.STARTING_POINT_A)

    async def set_starting_point_b(self, value: int) -> None:
        """Set starting point B and refresh it from EEPROM."""
        await self._device._write_eeprom_param(EepromParam.STARTING_POINT_B, value)
        await self._device._read_eeprom_param(EepromParam.STARTING_POINT_B)

    async def start_mowing(
        self,
        duration_minutes: int | None = None,
        starting_zone: int | None = None,
    ) -> None:
        """Start mowing, optionally with duration and zone."""
        duration_minutes = (
            max(1, min(0xFF, duration_minutes)) if duration_minutes is not None else 30
        )
        starting_zone = (
            max(0, min(0xFF, starting_zone)) if starting_zone is not None else 0x80
        )
        await self._device._send_msg_with_sequence(
            MessageType.COMMAND,
            struct.pack(
                ">BBB",
                OperationType.START_MOWING,
                starting_zone,
                duration_minutes,
            ),
        )
        await self._device._send_msg(MessageType.GET_MESSAGE)
        await self._device._send_misc_msg(MessageTypeMisc.STATE)

    async def start_mowing_edge(self) -> None:
        """Start edge mowing."""
        await self._device._send_msg_with_sequence(
            MessageType.COMMAND,
            struct.pack(">BB", OperationType.START_EDGE_MOWING, 0x80),
        )
        await self._device._send_msg(MessageType.GET_MESSAGE)
        await self._device._send_misc_msg(MessageTypeMisc.STATE)

    async def stop_mowing(self) -> None:
        """Stop mowing."""
        await self._device._send_msg_with_sequence(
            MessageType.COMMAND,
            struct.pack(">BB", OperationType.STOP_MOWING, 0xFF),
        )
        await self._device._send_msg(MessageType.GET_MESSAGE)
        await self._device._send_misc_msg(MessageTypeMisc.STATE)

    async def return_to_home(self) -> None:
        """Return mower to its home base."""
        await self._device._send_msg_with_sequence(
            MessageType.COMMAND,
            struct.pack(">BB", OperationType.RETURN_HOME, 0xBF),
        )
        await self._device._send_msg(MessageType.GET_MESSAGE)
        await self._device._send_misc_msg(MessageTypeMisc.STATE)

    async def update_date_time(self, timestamp: datetime | None = None) -> bool:
        """Update mower date and time."""
        timestamp = timestamp or datetime.now().astimezone()
        return await self._device._send_msg_with_sequence(
            MessageType.UPDATE_DATE_TIME,
            struct.pack(
                ">HBBHBBB",
                1,
                timestamp.day,
                timestamp.month,
                timestamp.year,
                timestamp.hour,
                timestamp.minute,
                0,
            ),
        )

    def handle_get_message(self, payload: bytes) -> None:
        """Handle GET_MESSAGE response packet."""
        if not self._device._check_payload_length(
            MessageType.GET_MESSAGE,
            payload,
            GET_STATUS_PAYLOAD_SIZE,
            exact=True,
        ):
            return

        (msgtype, msgid, stopid, _failureid) = struct.unpack_from(">BHHH", payload)

        if msgtype & MESSAGE_TYPE_STOP_ID_MASK:
            message = (
                ""
                if stopid == UNKNOWN_FIELD_VALUE
                else MessageRK.get_stop_message(stopid)
            )
            self._device._set_message("Error: " + str(message))
        else:
            message = (
                "" if msgid == UNKNOWN_FIELD_VALUE else MessageRK.get_message(msgid)
            )
            self._device._set_message(str(message))

    def handle_read_eeprom_response(self, request: Any, response: Any) -> None:
        """Handle a READ_EEPROM response after pending command matching."""
        expected_size = READ_EEPROM_PAYLOAD_SIZE * len(request.payload) // 2
        if not self._device._check_payload_length(
            MessageType.READ_EEPROM,
            response.payload,
            expected_size,
            exact=True,
        ):
            LOGGER.warning(
                "Received READ_EEPROM response with invalid payload length: %s",
                response.payload.hex(),
            )
            return

        for index in range(len(request.payload) // 2):
            field = struct.unpack_from(">H", request.payload, offset=index * 2)[0]
            value = struct.unpack_from(
                ">L",
                response.payload,
                offset=index * READ_EEPROM_PAYLOAD_SIZE,
            )[0]

            try:
                field_name = EepromParam(field).name
            except ValueError:
                field_name = f"0x{field:04X}"

            LOGGER.debug("  EEPROM: %s=0x%08X", field_name, value)

            if field == EepromParam.WIRE_SIGNAL_TYPE:
                self._device._set_wire_signal_type(value)
            elif field == EepromParam.STARTING_POINT_A:
                self._device._set_starting_point_a(value)
            elif field == EepromParam.STARTING_POINT_B:
                self._device._set_starting_point_b(value)

    def handle_miscellaneous_response(self, request: Any, response: Any) -> None:
        """Handle a MISCELLANEOUS response after pending command matching."""
        if not self._device._check_payload_length(
            MessageType.MISCELLANEOUS,
            response.payload,
            MISC_TYPE_SIZE,
        ):
            LOGGER.debug(
                "Matched response command counter 0x%04X to queued %s "
                "command: %s => %s",
                response.counter,
                request.msg_type.name,
                request.payload.hex(),
                response.payload.hex(),
            )
            return

        try:
            misc_type = MessageTypeMisc(struct.unpack_from(">H", response.payload)[0])
        except ValueError:
            LOGGER.warning(
                "Received MISCELLANEOUS response with unknown type: %s",
                response.payload.hex(),
            )
            return

        if misc_type == MessageTypeMisc.STATE:
            if not self._device._check_payload_length(
                MessageType.MISCELLANEOUS,
                response.payload,
                ROBOT_STATE_PAYLOAD_MIN_SIZE,
            ):
                return

            (
                byte_0,
                state,
                battery_level,
                next_departure,
                previous_departure,
                expected_duration,
                _one_time_setup,
                no_depart_reason,
                byte_10,
                byte_11,
                _byte_12,
                _charging_state,
            ) = struct.unpack_from(
                ">BBBHHBBBBBBB",
                response.payload,
                offset=MISC_TYPE_SIZE,
            )

            operation = byte_0 & 0x07
            program_enabled = byte_0 & 0x10 != 0

            anti_theft_enabled = byte_10 & 0x01 != 0
            anti_theft_active = byte_10 & 0x02 != 0
            child_lock_enabled = byte_10 & 0x10 != 0

            mower_home = byte_11 & 0x01 != 0
            disabling_device_removed = byte_11 & 0x02 != 0
            charging_active = byte_11 & 0x10 != 0

            self._device._set_program_enabled(program_enabled)
            self._device._set_anti_theft_enabled(anti_theft_enabled)
            self._device._set_child_lock_enabled(child_lock_enabled)
            self._device._set_anti_theft_active(anti_theft_active)
            self._device._set_mower_home(mower_home)
            self._device._set_charging_active(charging_active)
            self._device._set_disabling_device_removed(disabling_device_removed)
            self._device._set_state(
                self._device._describe_operating_state(state, operation)
            )
            self._device._set_battery_level(battery_level)
            self._device._set_next_departure(next_departure)
            self._device._set_previous_departure(previous_departure)
            self._device._set_expected_duration(expected_duration)
            self._device._set_no_depart_reason(
                ""
                if no_depart_reason == 0
                else str(MessageRT.get_message(no_depart_reason))
            )
        elif misc_type == MessageTypeMisc.INFO:
            if not self._device._check_payload_length(
                MessageType.MISCELLANEOUS,
                response.payload,
                INFO_PAYLOAD_SIZE,
                exact=True,
            ):
                return

            model, _max_cycles, _max_areas = struct.unpack_from(
                ">BBB",
                response.payload,
                offset=MISC_TYPE_SIZE,
            )
            self._device._set_model(model)
