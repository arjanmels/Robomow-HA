"""RT-family protocol handler for Robomow BLE."""

# ruff: noqa: SLF001

from __future__ import annotations

import datetime
import struct
from enum import IntEnum
from typing import Any

from .const import LOGGER, MessageType, MowerSchedule, WireSignalType, Zone
from .family_handler_base import RobomowFamilyHandler
from .helpers import check_payload_length
from .messages import MessageRK, MessageRT

UNKNOWN_FIELD_VALUE = 0xFFFF

GET_STATUS_PAYLOAD_SIZE = 7
READ_EEPROM_PAYLOAD_SIZE = 4
INFO_PAYLOAD_SIZE = 5
MISC_TYPE_SIZE = 2
ROBOT_STATE_PAYLOAD_MIN_SIZE = 17
MESSAGE_TYPE_STOP_ID_MASK = 0x2


class OperationType(IntEnum):
    """Operation types used in RT command messages."""

    STOP_MOWING = 0x0000
    START_EDGE_MOWING = 0x0001
    START_MOWING = 0x0002
    RETURN_HOME = 0x0003


class MiscMessageType(IntEnum):
    """RT miscellaneous message sub-types."""

    INFO = 0x08
    STATE = 0x0B
    GET_SCHEDULE = 0x0D
    SET_SCHEDULE = 0x3D
    # TODO(AM): check for correctness
    ANTI_THEFT_CONFIRM = 0x0C
    EXTENDED_STATE = 0x27
    LAST_OPERATIONS = 0x4C
    CONFIG_META_DATA = 0x4E
    SUPPORTED_FEATURES = 0x4F


class EepromParam(IntEnum):
    """RT-family EEPROM parameter identifiers."""

    STARTING_POINT_A = 0x000D
    STARTING_POINT_B = 0x000E

    SCHEDULE_ENABLED = 0x008C
    ANTI_THEFT_ENABLED = 0x00B9
    CHILD_LOCK_ENABLED = 0x00BC
    WIRE_SIGNAL_TYPE = 0x011F


class RobomowRtFamilyHandler(RobomowFamilyHandler):
    """RT-family Robomow BLE protocol behavior."""

    async def async_initialize_state(self) -> None:
        """Initialize RT-family state after connection."""
        await self._device._async_send_msg(MessageType.GET_MESSAGE)
        await self._device._async_send_misc_msg(MiscMessageType.INFO)
        await self._device._async_read_eeprom_param(
            EepromParam.CHILD_LOCK_ENABLED,
            EepromParam.ANTI_THEFT_ENABLED,
            EepromParam.SCHEDULE_ENABLED,
            EepromParam.WIRE_SIGNAL_TYPE,
            EepromParam.STARTING_POINT_A,
            EepromParam.STARTING_POINT_B,
        )
        await self._device._async_send_misc_msg(MiscMessageType.GET_SCHEDULE)

    async def async_poll_status(self) -> None:
        """Poll RT-family status while connected."""
        await self._device._async_send_msg(MessageType.GET_MESSAGE)
        await self._device._async_send_misc_msg(MiscMessageType.STATE)
        await self._device._async_read_eeprom_param(
            EepromParam.CHILD_LOCK_ENABLED,
            EepromParam.ANTI_THEFT_ENABLED,
        )

    async def async_enable_schedule(self) -> None:
        """Enable the mower schedule."""
        await self._device._async_write_eeprom_param(EepromParam.SCHEDULE_ENABLED, 1)
        await self._device._async_send_misc_msg(MiscMessageType.STATE)

    async def async_disable_schedule(self) -> None:
        """Disable the mower schedule."""
        await self._device._async_write_eeprom_param(EepromParam.SCHEDULE_ENABLED, 0)
        await self._device._async_send_misc_msg(MiscMessageType.STATE)

    async def async_enable_anti_theft(self) -> None:
        """Enable anti-theft mode."""
        await self._device._async_write_eeprom_param(EepromParam.ANTI_THEFT_ENABLED, 1)
        await self._device._async_send_misc_msg(MiscMessageType.STATE)

    async def async_disable_anti_theft(self) -> None:
        """Disable anti-theft mode."""
        await self._device._async_write_eeprom_param(EepromParam.ANTI_THEFT_ENABLED, 0)
        await self._device._async_send_misc_msg(MiscMessageType.STATE)

    async def async_enable_child_lock(self) -> None:
        """Enable child lock mode."""
        await self._device._async_write_eeprom_param(EepromParam.CHILD_LOCK_ENABLED, 1)
        await self._device._async_send_misc_msg(MiscMessageType.STATE)
        await self._device._async_read_eeprom_param(EepromParam.CHILD_LOCK_ENABLED)

    async def async_disable_child_lock(self) -> None:
        """Disable child lock mode."""
        await self._device._async_write_eeprom_param(EepromParam.CHILD_LOCK_ENABLED, 0)
        await self._device._async_send_misc_msg(MiscMessageType.STATE)
        await self._device._async_read_eeprom_param(EepromParam.CHILD_LOCK_ENABLED)

    async def async_set_wire_signal_type(
        self, wire_signal_type: WireSignalType
    ) -> None:
        """Set wire signal type and refresh it from EEPROM."""
        await self._device._async_write_eeprom_param(
            EepromParam.WIRE_SIGNAL_TYPE, int(wire_signal_type)
        )
        await self._device._async_read_eeprom_param(EepromParam.WIRE_SIGNAL_TYPE)

    async def async_set_starting_point_a(self, value: int) -> None:
        """Set starting point A and refresh it from EEPROM."""
        await self._device._async_write_eeprom_param(
            EepromParam.STARTING_POINT_A, value
        )
        await self._device._async_read_eeprom_param(EepromParam.STARTING_POINT_A)

    async def async_set_starting_point_b(self, value: int) -> None:
        """Set starting point B and refresh it from EEPROM."""
        await self._device._async_write_eeprom_param(
            EepromParam.STARTING_POINT_B, value
        )
        await self._device._async_read_eeprom_param(EepromParam.STARTING_POINT_B)

    async def async_start_mowing(
        self,
        duration_minutes: int | None = None,
        starting_zone: Zone | None = None,
    ) -> None:
        """Start mowing, optionally with duration and zone."""
        duration_minutes = (
            max(1, min(0xFF, duration_minutes)) if duration_minutes is not None else 30
        )
        starting_zone = starting_zone if starting_zone is not None else Zone.MAIN

        await self._device._async_send_msg_with_sequence(
            MessageType.COMMAND,
            struct.pack(
                ">BBB",
                OperationType.START_MOWING,
                starting_zone.value | 0x80,
                duration_minutes,
            ),
        )
        await self._device._async_send_misc_msg(MiscMessageType.STATE)
        await self._device._async_send_msg(MessageType.GET_MESSAGE)

    async def async_start_mowing_edge(self) -> None:
        """Start edge mowing."""
        await self._device._async_send_msg_with_sequence(
            MessageType.COMMAND,
            struct.pack(">BB", OperationType.START_EDGE_MOWING, 0x80),
        )
        await self._device._async_send_misc_msg(MiscMessageType.STATE)
        await self._device._async_send_msg(MessageType.GET_MESSAGE)

    async def async_stop_mowing(self) -> None:
        """Stop mowing."""
        await self._device._async_send_msg_with_sequence(
            MessageType.COMMAND,
            struct.pack(">BB", OperationType.STOP_MOWING, 0xFF),
        )
        await self._device._async_send_misc_msg(MiscMessageType.STATE)
        await self._device._async_send_msg(MessageType.GET_MESSAGE)

    async def async_return_to_home(self) -> None:
        """Return mower to its home base."""
        await self._device._async_send_msg_with_sequence(
            MessageType.COMMAND,
            struct.pack(">BB", OperationType.RETURN_HOME, 0xBF),
        )
        await self._device._async_send_misc_msg(MiscMessageType.STATE)
        await self._device._async_send_msg(MessageType.GET_MESSAGE)

    async def async_set_schedule(self, schedule: MowerSchedule) -> None:
        """Set the mower schedule."""
        days = schedule.day
        await self._device._async_send_misc_msg(
            MiscMessageType.SET_SCHEDULE,
            struct.pack(
                ">BBBHH7B7B7BB",
                0xFF,
                sum(d.enabled << i for i, d in enumerate(days)),
                self._device._schedule_enabled,
                schedule.start_time.hour * 60 + schedule.start_time.minute,
                schedule.end_time.hour * 60 + schedule.end_time.minute,
                *(day.duration for day in reversed(days)),
                *(day.cycles for day in reversed(days)),
                *(day.zone.value for day in reversed(days)),
                0,
            ),
        )
        await self._device._async_send_misc_msg(MiscMessageType.GET_SCHEDULE)
        await self._device._async_send_msg(MessageType.GET_CONFIG)

    def handle_get_message(self, payload: bytes | bytearray | memoryview) -> None:
        """Handle GET_MESSAGE response packet."""
        if not check_payload_length(
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
        if not check_payload_length(
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

    def handle_miscellaneous_response(self, response: Any) -> None:
        """Handle a MISCELLANEOUS response after pending command matching."""
        if not check_payload_length(
            MessageType.MISCELLANEOUS,
            response.payload,
            MISC_TYPE_SIZE,
        ):
            return

        try:
            misc_type = MiscMessageType(struct.unpack_from(">H", response.payload)[0])
        except ValueError:
            LOGGER.warning(
                "Received MISCELLANEOUS response with unknown type: %s",
                response.payload.hex(),
            )
            return

        if misc_type == MiscMessageType.INFO:
            self._handle_misc_info(response.payload)
            return

        if misc_type == MiscMessageType.STATE:
            self._handle_misc_state(response.payload)
            return

        if misc_type == MiscMessageType.GET_SCHEDULE:
            self._handle_misc_schedule(response.payload)
            return

        LOGGER.debug(
            "Received unhandled MISCELLANEOUS response with type %s: %s",
            misc_type,
            response.payload.hex(),
        )

    def _handle_misc_info(self, payload: bytes | bytearray | memoryview) -> None:
        """Handle INFO miscellaneous payload."""
        if not check_payload_length(
            MessageType.MISCELLANEOUS,
            payload,
            INFO_PAYLOAD_SIZE,
            exact=True,
        ):
            return

        model, max_cycles, max_areas = struct.unpack_from(
            ">BBB",
            payload,
            offset=MISC_TYPE_SIZE,
        )
        self._device._set_model(model)

        LOGGER.debug(
            "  INFO: model=%d max_cycles=%d max_areas=%d",
            model,
            max_cycles,
            max_areas,
        )

    def _handle_misc_state(self, payload: bytes | bytearray | memoryview) -> None:
        """Handle STATE miscellaneous payload."""
        if not check_payload_length(
            MessageType.MISCELLANEOUS,
            payload,
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
            byte_12,
            _charging_state,
        ) = struct.unpack_from(
            ">BBBHHBBBBBBB",
            payload,
            offset=MISC_TYPE_SIZE,
        )

        operation = byte_0 & 0x07
        schedule_enabled = byte_0 & 0x10 != 0

        anti_theft_enabled = byte_10 & 0x01 != 0
        anti_theft_active = byte_10 & 0x02 != 0
        child_lock_enabled = byte_10 & 0x10 != 0

        mower_home = byte_11 & 0x01 != 0
        disabling_device_removed = byte_11 & 0x02 != 0
        charging_active = byte_11 & 0x10 != 0

        LOGGER.debug(
            "  STATE: operation=%d state=%d battery=%d "
            "_one_time_setup=%d no_depart_reason=%d _byte_10=%d byte_11=%d byte_12=%d\n"
            "  next_departure=%d previous_departure=%d expected_duration=%d "
            "anti_theft_enabled=%s anti_theft_active=%s child_lock_enabled=%s"
            "  mower_home=%s disabling_device_removed=%s charging_active=%s",
            operation,
            state,
            battery_level,
            _one_time_setup,
            no_depart_reason,
            byte_10,
            byte_11,
            byte_12,
            next_departure,
            previous_departure,
            expected_duration,
            anti_theft_enabled,
            anti_theft_active,
            child_lock_enabled,
            mower_home,
            disabling_device_removed,
            charging_active,
        )

        self._device._set_schedule_enabled(schedule_enabled)
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

    def _handle_misc_schedule(self, payload: bytes | bytearray | memoryview) -> None:
        """Handle GET_SCHEDULE miscellaneous payload."""
        enabled_days, schedule_enabled, start_time, end_time = struct.unpack_from(
            ">BBHH",
            payload,
            offset=MISC_TYPE_SIZE,
        )
        byte_27 = payload[MISC_TYPE_SIZE + 27]  # unused turbo/edge mode?
        byte_28 = payload[MISC_TYPE_SIZE + 28]  # unused turbo/edge mode?
        schedule_enabled = schedule_enabled != 0

        schedule: MowerSchedule = MowerSchedule(
            start_time=datetime.time(hour=start_time // 60, minute=start_time % 60),
            end_time=datetime.time(hour=end_time // 60, minute=end_time % 60),
        )

        LOGGER.debug(
            "  GET_SCHEDULE: "
            "schedule_enabled=%s start_time=%s end_time=%s byte_27=%s byte_28=%s",
            schedule_enabled,
            schedule.start_time,
            schedule.end_time,
            byte_27,
            byte_28,
        )

        for i in range(7):
            schedule.day[i].enabled = (enabled_days & (1 << i)) != 0
            schedule.day[i].duration = payload[MISC_TYPE_SIZE + 6 + (6 - i)]
            schedule.day[i].cycles = payload[MISC_TYPE_SIZE + 13 + (6 - i)]
            schedule.day[i].zone = Zone(payload[MISC_TYPE_SIZE + 20 + (6 - i)])

            LOGGER.debug(
                "  Day %d: enabled=%s duration=%d zone=%d cycles=%d",
                i,
                schedule.day[i].enabled,
                schedule.day[i].duration,
                schedule.day[i].zone,
                schedule.day[i].cycles,
            )

        self._device._set_schedule(schedule)
