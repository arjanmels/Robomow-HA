"""BLE device data structures for the Robomow integration."""

from __future__ import annotations

import asyncio
import struct
from collections import deque
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, NamedTuple

from bleak.exc import (
    BleakCharacteristicNotFoundError,
    BleakDeviceNotFoundError,
    BleakError,
)
from bleak_retry_connector import (
    BleakClientWithServiceCache,
    establish_connection,
)
from bluetooth_data_tools import short_address
from bluetooth_sensor_state_data import BluetoothData
from homeassistant.components.bluetooth import async_ble_device_from_address
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.event import async_track_time_interval

from custom_components.robomow_ble.messages import MessageRK

from .const import (
    AUTH_RESPONSE_LENGTH,
    LOGGER,
    MESSAGE_RECEIVE_BYTE,
    MESSAGE_SEND_BYTE,
    MESSAGE_START_BYTE,
    MINIMUM_MESSAGE_LENGTH,
    UUID_CHAR_AUTHENTICATE,
    UUID_CHAR_DATA_IN,
    UUID_CHAR_DATA_OUT,
    UUID_SERVICE,
    EepromParam,
    MessageType,
    MessageTypeMisc,
    MowerFamily,
    OperationType,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from bleak.backends.characteristic import BleakGATTCharacteristic
    from bleak.backends.service import BleakGATTService
    from homeassistant.components.bluetooth import (
        BluetoothServiceInfoBleak as BluetoothServiceInfo,
    )
    from homeassistant.core import HomeAssistant


RESPONSE_COMMAND_COUNTER_SIZE = 2
GET_CONFIG_PAYLOAD_MIN_SIZE = 5
GET_STATUS_PAYLOAD_SIZE = 7
PROGRAM_ENABLED_PAYLOAD_SIZE = 4
MISC_TYPE_SIZE = 2
ROBOT_STATE_PAYLOAD_MIN_SIZE = 17


class PendingCommand(NamedTuple):
    """Command metadata kept in the pending-response FIFO queue."""

    counter: int
    msg_type: MessageType
    payload: bytes


class RoboMowBLEDevice:
    """Representation of a Robomow BLE device."""

    def __init__(
        self, hass: HomeAssistant, address: str, mainboard_serial: str
    ) -> None:
        """Initialize the device."""
        self._hass: HomeAssistant = hass
        self._address: str = address
        self._mainboard_serial: bytes = (
            mainboard_serial.strip().encode("utf-8") + b"\x00"
        )

        self._client: BleakClientWithServiceCache | None = None
        self._service: BleakGATTService | None = None
        self._char_auth: BleakGATTCharacteristic | None = None
        self._char_data_in: BleakGATTCharacteristic | None = None
        self._char_data_out: BleakGATTCharacteristic | None = None
        self._command_counter: int = 0
        self._pending_commands: deque[PendingCommand] = deque()
        self._receive_buffer: bytearray = bytearray()
        self._state_listeners: set[Callable[[], None]] = set()
        self._date_time_poll_cancel: Callable[[], None] | None = None
        self._status_poll_cancel: Callable[[], None] | None = None

        self._family: MowerFamily | None = None
        self._software_version: int | None = None
        self._software_release: int | None = None
        self._mainboard_version: int | None = None
        self._program_enabled: bool | None = None
        self._status: str | None = None
        self._operating_state: str | None = None
        self._mowing_duration: int = 30

    # --- State listeners ---

    def add_state_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        """Register a callback for connection/program state changes."""
        self._state_listeners.add(listener)

        def _remove_listener() -> None:
            self._state_listeners.discard(listener)

        return _remove_listener

    def _notify_state_listeners(self) -> None:
        """Notify listeners that connection or program state changed."""
        for listener in tuple(self._state_listeners):
            listener()

    def _set_program_enabled(self, enabled: bool | None) -> None:  # noqa: FBT001
        """Update program_enabled and emit change callbacks when needed."""
        if self._program_enabled == enabled:
            return
        self._program_enabled = enabled
        self._notify_state_listeners()

    def _set_status(self, status: str | None) -> None:
        """Update status text and emit change callbacks when needed."""
        if self._status == status:
            return
        self._status = status
        self._notify_state_listeners()

    def _set_operating_state(self, operating_state: str | None) -> None:
        """Update operating state text and emit change callbacks when needed."""
        if self._operating_state == operating_state:
            return
        self._operating_state = operating_state
        self._notify_state_listeners()

    # --- Internal state helpers ---

    def _cancel_periodic_polling(self) -> None:
        """Cancel all active periodic polling callbacks."""
        if self._date_time_poll_cancel is not None:
            self._date_time_poll_cancel()
            self._date_time_poll_cancel = None

        if self._status_poll_cancel is not None:
            self._status_poll_cancel()
            self._status_poll_cancel = None

    def _initialize_runtime_state(self) -> None:
        """Initialize runtime state after a successful BLE connection."""
        self._command_counter = 0
        self._pending_commands.clear()
        self._receive_buffer.clear()
        self._set_status(None)
        self._set_operating_state(None)
        self._set_program_enabled(None)
        self._notify_state_listeners()

    def _teardown_connection(self) -> None:
        """Clear connection state, cancel polling, and notify listeners."""
        self._client = None
        self._service = None
        self._char_auth = None
        self._char_data_in = None
        self._char_data_out = None
        self._initialize_runtime_state()

    async def _establish_client_connection(self) -> None:
        """Resolve BLE device and establish a paired client connection."""
        ble_device = async_ble_device_from_address(
            self._hass, self._address, connectable=True
        )
        if ble_device is None:
            raise BleakDeviceNotFoundError(self._address)

        self._client = await establish_connection(
            BleakClientWithServiceCache,
            ble_device,
            ble_device.address,
            disconnected_callback=self._handle_disconnect,
        )
        await self._client.pair()

    def _resolve_characteristics(self) -> None:
        """Resolve GATT service and required characteristics for this device."""
        if self._client is None:
            return

        self._service = self._client.services.get_service(UUID_SERVICE)
        if self._service is None:
            raise BleakCharacteristicNotFoundError(UUID_SERVICE)

        self._char_auth = self._service.get_characteristic(UUID_CHAR_AUTHENTICATE)
        if self._char_auth is None:
            raise BleakCharacteristicNotFoundError(UUID_CHAR_AUTHENTICATE)

        self._char_data_in = self._service.get_characteristic(UUID_CHAR_DATA_IN)
        if self._char_data_in is None:
            raise BleakCharacteristicNotFoundError(UUID_CHAR_DATA_IN)

        self._char_data_out = self._service.get_characteristic(UUID_CHAR_DATA_OUT)
        if self._char_data_out is None:
            raise BleakCharacteristicNotFoundError(UUID_CHAR_DATA_OUT)

    async def _authenticate_connection(self) -> None:
        """Authenticate by writing the mainboard serial and validating response."""
        if self._client is None:
            return
        if self._char_auth is None:
            raise BleakCharacteristicNotFoundError(UUID_CHAR_AUTHENTICATE)

        await self._client.write_gatt_char(
            self._char_auth, self._mainboard_serial, response=True
        )

        auth_response = await self._client.read_gatt_char(self._char_auth)
        if len(auth_response) != AUTH_RESPONSE_LENGTH or (
            any(byte != 0x01 for byte in auth_response)
            and auth_response != self._mainboard_serial
        ):
            LOGGER.debug(
                "Authentication failed: invalid response payload: %s",
                auth_response.hex(),
            )
            raise ConfigEntryAuthFailed

    async def _start_notifications(self) -> None:
        """Start notifications for incoming mower packets."""
        if self._client is None:
            return
        if self._char_data_in is None:
            raise BleakCharacteristicNotFoundError(UUID_CHAR_DATA_IN)

        await self._client.start_notify(self._char_data_in, self._handle_data_received)

    @property
    def address(self) -> str:
        """Return the device address."""
        return self._address

    @property
    def mainboard_serial(self) -> str:
        """Return the mainboard serial number."""
        return self._mainboard_serial.decode("utf-8").rstrip("\x00")

    @property
    def family(self) -> MowerFamily:
        """Return the mower family, if known."""
        return self._family or MowerFamily.Unknown

    @family.setter
    def family(self, value: MowerFamily | int) -> None:
        self._family = MowerFamily(value)

    @property
    def mainboard_version(self) -> int | None:
        """Return the mainboard version, if known."""
        return self._mainboard_version

    @property
    def software_version(self) -> int | None:
        """Return the software version, if known."""
        return self._software_version

    @property
    def software_release(self) -> int | None:
        """Return the software release, if known."""
        return self._software_release

    @property
    def program_enabled(self) -> bool | None:
        """Return whether the mower program is enabled, if known."""
        return self._program_enabled

    @property
    def status(self) -> str | None:
        """Return the latest mower status text, if known."""
        return self._status

    @property
    def operating_state(self) -> str | None:
        """Return the latest mower operating state text, if known."""
        return self._operating_state

    @property
    def mowing_duration(self) -> int:
        """Return the configured mowing duration in minutes."""
        return self._mowing_duration

    @mowing_duration.setter
    def mowing_duration(self, value: int) -> None:
        """Set the mowing duration in minutes (1-255)."""
        self._mowing_duration = max(1, min(255, value))

    def is_connected(self) -> bool:
        """Return True if the client is connected."""
        return self._client is not None and self._client.is_connected

    # --- Connection lifecycle ---

    async def connect(self) -> None:
        """Create and connect a Robomow BLE client."""
        if self._client is not None and self._client.is_connected:
            LOGGER.debug("BLE client already connected for address %s", self._address)
            return

        LOGGER.debug("Connecting to Robomow BLE device at address %s", self._address)

        try:
            await self._establish_client_connection()
            self._resolve_characteristics()
            await self._authenticate_connection()
            await self._start_notifications()
        except BleakError:
            await self.disconnect()
            raise

        self._initialize_runtime_state()

        # Start periodic date/time updates
        self._start_date_time_polling()

        # Start periodic GET_STATUS polling
        self._start_status_polling()

        await self._send_msg(MessageType.GET_CONFIG)
        await self._send_msg(MessageType.GET_STATUS)
        await self._read_eeprom_param(EepromParam.PROGRAM_ENABLED)

    async def disconnect(self) -> None:
        """Disconnect the BLE client."""
        LOGGER.debug("BLE client disconnect called")
        self._cancel_periodic_polling()
        if self._client is not None and self._client.is_connected:
            if self._char_data_in is not None:
                await self._client.stop_notify(self._char_data_in)
            await self._client.disconnect()

    def __del__(self) -> None:
        """Clean up the BLE connection when the instance is garbage collected."""
        LOGGER.debug("RoboMowBLEDevice instance is being garbage collected")
        if self._client is not None and self._client.is_connected:
            self._hass.async_create_task(self._client.disconnect())

    # --- Packet I/O ---

    async def _write_value(self, data: bytes) -> bool:
        """Write a packet payload to the mower data output characteristic."""
        if not self.is_connected() or not self._client or not self._char_data_out:
            return False

        await self._client.write_gatt_char(self._char_data_out, data, response=True)
        return True

    @staticmethod
    def _calculate_checksum(data: bytes) -> int:
        """Calculate packet checksum by XORing 0xFF with the byte sum."""
        return (~sum(data)) & 0xFF

    async def _send_msg(
        self, msg_type: MessageType, extra: bytes | None = None
    ) -> bool:
        """Update packet checksum and write it to the BLE characteristic."""
        extra = extra or b""

        if len(extra) > 0:
            LOGGER.debug(
                "Sending packet with msg_type %s and extra data: %s",
                msg_type.name,
                extra.hex(),
            )
        else:
            LOGGER.debug("Sending packet with msg_type %s", msg_type.name)

        packet = struct.pack(
            ">BBBB", MESSAGE_START_BYTE, 5 + len(extra), MESSAGE_SEND_BYTE, msg_type
        )
        packet += extra
        packet += struct.pack(">B", self._calculate_checksum(packet))

        return await self._write_value(packet)

    async def _send_msg_with_sequence(
        self, msg_type: MessageType, payload: bytes
    ) -> bool:
        """Send a message with a 2-byte command counter and the given payload."""
        command_counter = self._command_counter = self._command_counter + 1
        buf = struct.pack(">H", command_counter) + payload
        pending_command = PendingCommand(command_counter, msg_type, payload)
        self._pending_commands.append(pending_command)
        sent = await self._send_msg(msg_type, buf)
        if not sent:
            self._pending_commands.remove(pending_command)

        return sent

    async def _send_misc_msg(self, misc_type: MessageTypeMisc) -> bool:
        """Send a miscellaneous message with the given type and command counter."""
        return await self._send_msg_with_sequence(
            MessageType.MISCELLANEOUS, struct.pack(">H", misc_type)
        )

    # --- Polling ---

    def _start_date_time_polling(self) -> None:
        """Start sending date/time updates every minute while connected."""
        if not self.is_connected():
            return

        self._date_time_poll_cancel = async_track_time_interval(
            self._hass,
            self._on_date_time_poll,
            timedelta(seconds=60),
        )

    async def _on_date_time_poll(self, _now: datetime) -> None:
        """Send periodic date/time update while connected."""
        await self.update_date_time()

    def _start_status_polling(self) -> None:
        """Start sending GET_STATUS every 10 seconds while connected."""
        if not self.is_connected():
            return

        self._status_poll_cancel = async_track_time_interval(
            self._hass,
            self._on_status_poll,
            timedelta(seconds=2),
        )

    async def _on_status_poll(self, _now: datetime) -> None:
        """Send periodic GET_STATUS command while connected."""
        await self._send_msg(MessageType.GET_STATUS)
        await self._send_misc_msg(MessageTypeMisc.ROBOT_STATE)

    # --- EEPROM / commands ---

    async def _read_eeprom_param(self, param: EepromParam) -> bool:
        """Send a message to read an EEPROM parameter with the given ID."""
        return await self._send_msg_with_sequence(
            MessageType.READ_EEPROM, struct.pack(">H", param)
        )

    async def _write_eeprom_param(self, param: EepromParam, payload: bytes) -> bool:
        """Send a message to write an EEPROM parameter with the given ID and payload."""
        return await self._send_msg_with_sequence(
            MessageType.WRITE_EEPROM, struct.pack(">H", param) + payload
        )

    async def enable_program(self) -> bool:
        """Send a message to enable the mower program."""
        await self._write_eeprom_param(
            EepromParam.PROGRAM_ENABLED, struct.pack(">L", 1)
        )
        return await self._read_eeprom_param(EepromParam.PROGRAM_ENABLED)

    async def disable_program(self) -> bool:
        """Send a message to disable the mower program."""
        await self._write_eeprom_param(
            EepromParam.PROGRAM_ENABLED, struct.pack(">L", 0)
        )
        return await self._read_eeprom_param(EepromParam.PROGRAM_ENABLED)

    async def start_mowing(self, duration_minutes: int | None = None) -> bool:
        """Send a message to start the mower program, optionally with a duration."""
        duration_minutes = duration_minutes or self.mowing_duration
        await self._send_msg_with_sequence(
            MessageType.COMMAND,
            struct.pack(">BBB", OperationType.START_MOWING, 0x80, duration_minutes),
        )
        return await self._send_msg(MessageType.GET_STATUS)

    async def start_mowing_edge(self) -> bool:
        """Send a message to start edge mowing."""
        await self._send_msg_with_sequence(
            MessageType.COMMAND,
            struct.pack(">BB", OperationType.START_EDGE_MOWING, 0x80),
        )
        return await self._send_msg(MessageType.GET_STATUS)

    async def stop_mowing(self) -> bool:
        """Send a message to stop the mower program."""
        await self._send_msg_with_sequence(
            MessageType.COMMAND, struct.pack(">BB", OperationType.STOP_MOWING, 0xFF)
        )
        return await self._send_msg(MessageType.GET_STATUS)

    async def return_to_home(self) -> bool:
        """Send a message to return the mower to its home base."""
        await self._send_msg_with_sequence(
            MessageType.COMMAND, struct.pack(">BB", OperationType.RETURN_HOME, 0xBF)
        )
        return await self._send_msg(MessageType.GET_STATUS)

    async def update_date_time(self, timestamp: datetime | None = None) -> bool:
        """Send a message to update the mower date and time."""
        timestamp = timestamp or datetime.now().astimezone()
        return await self._send_msg_with_sequence(
            MessageType.UPDATE_DATE_TIME,
            struct.pack(
                ">HBBHBBB",
                1,
                timestamp.day,
                timestamp.month,
                timestamp.year,
                timestamp.hour,
                timestamp.minute,
                # The mower's update-time payload is sent with minute-level precision,
                # so seconds are intentionally set to 0.
                0,
            ),
        )

    # --- Response matching ---

    def _pop_pending_command(
        self, command_counter: int, msg_type: MessageType
    ) -> PendingCommand | None:
        """Pop the matching pending command for a response command counter."""
        for index, pending in enumerate(self._pending_commands):
            if pending.counter != command_counter:
                continue

            skipped = [self._pending_commands.popleft() for _ in range(index)]
            if skipped:
                LOGGER.warning(
                    (
                        "Detected %d missing response(s) before command counter "
                        "%d for %s: %s"
                    ),
                    len(skipped),
                    command_counter,
                    self._address,
                    ", ".join(str(command.counter) for command in skipped),
                )

            cmd = self._pending_commands.popleft()
            if msg_type not in (MessageType.ACKNOWLEDGE, cmd.msg_type):
                LOGGER.warning(
                    (
                        "Expected response of type %s for command counter %d but "
                        "got type %s from %s"
                    ),
                    cmd.msg_type.name,
                    command_counter,
                    msg_type.name,
                    self._address,
                )
                return None
            return cmd

        LOGGER.warning(
            "Received response for unknown command counter %d from %s",
            command_counter,
            self._address,
        )
        return None

    # --- BLE event handlers ---

    def _handle_disconnect(self, _client: BleakClientWithServiceCache) -> None:
        """Handle BLE disconnect callback."""
        LOGGER.debug("BLE client disconnected for address %s", self._address)
        self._cancel_periodic_polling()
        self._teardown_connection()

    def _handle_data_received(self, _sender: object, data: bytearray) -> None:
        """Handle BLE notifications."""
        self._receive_buffer.extend(data)

        while len(self._receive_buffer) >= MINIMUM_MESSAGE_LENGTH:
            if (
                self._receive_buffer[0] != MESSAGE_START_BYTE
                or self._receive_buffer[2] != MESSAGE_RECEIVE_BYTE
            ):
                LOGGER.warning(
                    "Received malformed packet from %s: %s",
                    self._address,
                    self._receive_buffer.hex(),
                )
                del self._receive_buffer[0]
                continue

            packet_len = self._receive_buffer[1]
            if len(self._receive_buffer) < packet_len:
                return

            packet = self._receive_buffer[:packet_len]
            self._receive_buffer = self._receive_buffer[packet_len:]

            if self._calculate_checksum(packet[:-1]) != packet[-1]:
                LOGGER.warning(
                    "Received packet with invalid checksum from %s: %s",
                    self._address,
                    packet.hex(),
                )
                continue

            try:
                msg_type = MessageType(packet[3])
            except ValueError:
                LOGGER.warning(
                    "Received packet with unknown msg_type 0x%02X from %s: %s",
                    packet[3],
                    self._address,
                    packet.hex(),
                )
                continue

            self._process_message(msg_type, packet[4:-1])

    def _check_payload_length(
        self,
        msg_type: MessageType,
        payload: bytes,
        expected_length: int,
        *,
        exact: bool = False,
    ) -> bool:
        """
        Validate payload length and log warning if invalid; return validity.

        Args:
            msg_type: The message type of the payload to validate.
            payload: The payload bytes to validate.
            expected_length: Minimum (or exact) length required.
            exact: If True, check for exact length; if False, check for minimum.

        """
        is_valid = (
            len(payload) == expected_length
            if exact
            else len(payload) >= expected_length
        )
        if not is_valid:
            LOGGER.warning(
                "Payload %s (expected %d, got %d) for %s: %s",
                "length mismatch" if exact else "too short",
                expected_length,
                len(payload),
                msg_type.name,
                payload.hex(),
            )
        return is_valid

    def _process_message(self, msg_type: MessageType, payload: bytes) -> None:
        """Dispatch a complete received packet to the appropriate handler."""
        LOGGER.debug(
            "Processing packet from %s with msg_type %s and payload: %s",
            self._address,
            msg_type.name,
            payload.hex(),
        )

        if msg_type == MessageType.GET_CONFIG:
            self._handle_get_config(payload)
        elif msg_type == MessageType.GET_STATUS:
            self._handle_get_status(payload)
        elif msg_type in (
            MessageType.ACKNOWLEDGE,
            MessageType.MISCELLANEOUS,
            MessageType.READ_EEPROM,
        ):
            self._handle_sequenced_response(msg_type, payload)

    def _handle_get_config(self, payload: bytes) -> None:
        """Handle a GET_CONFIG response packet."""
        if not self._check_payload_length(
            MessageType.GET_CONFIG, payload, GET_CONFIG_PAYLOAD_MIN_SIZE
        ):
            return

        (
            self.family,
            self._software_version,
            self._software_release,
            self._mainboard_version,
        ) = struct.unpack_from(">BBHB", payload)
        LOGGER.debug(
            (
                "Updated device info for %s: family=%s, software_version=%s, "
                "software_release=%s, mainboard_version=%s"
            ),
            self._address,
            self.family.name,
            self._software_version,
            self._software_release,
            self._mainboard_version,
        )

    def _handle_get_status(self, payload: bytes) -> None:
        """Handle a GET_STATUS response packet."""
        if not self._check_payload_length(
            MessageType.GET_STATUS, payload, GET_STATUS_PAYLOAD_SIZE, exact=True
        ):
            return

        (msgtype, msgid, stopid, _failureid) = struct.unpack_from(">BHHH", payload)
        message = (
            MessageRK.get_message(msgid)
            if msgtype == 1
            else MessageRK.get_stop_message(stopid)
        )
        self._set_status(str(message))
        LOGGER.debug("Updated mower status for %s: %s", self._address, self._status)

    def _handle_sequenced_response(self, msg_type: MessageType, payload: bytes) -> None:
        """Handle a sequenced response: extract counter, match command, delegate."""
        if not self._check_payload_length(
            msg_type, payload, RESPONSE_COMMAND_COUNTER_SIZE
        ):
            return

        command_counter = struct.unpack_from(">H", payload)[0]
        response = PendingCommand(command_counter, msg_type, payload[2:])

        request = self._pop_pending_command(response.counter, msg_type)
        if not request:
            LOGGER.warning(
                "Received %s response with unknown command counter %d from %s",
                msg_type.name,
                command_counter,
                self._address,
            )
            return

        if msg_type == MessageType.READ_EEPROM:
            self._handle_read_eeprom_response(request, response)
        elif msg_type == MessageType.MISCELLANEOUS:
            self._handle_miscellaneous_response(request, response)
        else:
            LOGGER.debug(
                "Matched response command counter %d to queued %s command: %s => %s",
                command_counter,
                request.msg_type.name,
                request.payload.hex(),
                response.payload.hex(),
            )

    def _handle_read_eeprom_response(
        self, request: PendingCommand, response: PendingCommand
    ) -> None:
        """Handle a READ_EEPROM response after the pending command has been matched."""
        LOGGER.debug(
            "Received READEEPROM response for command counter %d: %s => %s",
            response.counter,
            request.payload.hex(),
            response.payload.hex(),
        )

        if struct.unpack_from(">H", request.payload)[0] != EepromParam.PROGRAM_ENABLED:
            return

        if not self._check_payload_length(
            MessageType.READ_EEPROM, response.payload, PROGRAM_ENABLED_PAYLOAD_SIZE
        ):
            return

        self._set_program_enabled(struct.unpack_from(">L", response.payload)[0] != 0)
        LOGGER.debug("Program enabled: %s", self._program_enabled)

    def _describe_automatic_operation(self, operation: int) -> str:
        """Return human-readable text for automatic operation mode."""
        return {
            0: "Idle (Automatic)",
            1: "Mowing",
            2: "Edge Mowing",
            3: "Returning Home",
            4: "Learning Entry Point",
        }.get(operation, f"Unknown Automatic ({operation})")

    def _describe_operating_state(self, state: int, operation: int) -> str:
        """Return human-readable text for the mower operating state."""
        return {
            1: "Idle",
            2: "Charging",
            3: self._describe_automatic_operation(operation),
            4: "Remote Control",
            5: "Bit",
        }.get(state, f"Unknown ({state})")

    def _handle_miscellaneous_response(
        self, request: PendingCommand, response: PendingCommand
    ) -> None:
        """Handle a MISCELLANEOUS response after matching the pending command."""
        if not self._check_payload_length(
            MessageType.MISCELLANEOUS, response.payload, MISC_TYPE_SIZE
        ):
            LOGGER.debug(
                "Matched response command counter %d to queued %s command: %s => %s",
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
                "Received MISCELLANEOUS response with unknown type from %s: %s",
                self._address,
                response.payload.hex(),
            )
            return

        if misc_type == MessageTypeMisc.ROBOT_STATE:
            if not self._check_payload_length(
                MessageType.MISCELLANEOUS,
                response.payload,
                ROBOT_STATE_PAYLOAD_MIN_SIZE,
            ):
                return

            operation, state = struct.unpack_from(
                ">BB", response.payload, offset=MISC_TYPE_SIZE
            )
            self._set_operating_state(
                self._describe_operating_state(state & 0xF, operation & 0x7)
            )

            LOGGER.debug(
                "Received ROBOT_STATE response for command counter %d: %s => %s",
                response.counter,
                request.payload.hex(),
                response.payload.hex(),
            )


class RoboMowBLEDeviceData(BluetoothData):
    """Data about a Robomow BLE device."""

    def _start_update(self, service_info: BluetoothServiceInfo) -> None:
        """Update from BLE advertisement data."""
        LOGGER.debug(
            "Processing Bluetooth service info (_start_update): %s", service_info
        )
        self.set_device_manufacturer("RoboMow")
        self.set_device_name(service_info.name)
        self.set_precision(2)

        if UUID_SERVICE in map(str.lower, service_info.service_uuids or []):
            LOGGER.debug("Processing Bluetooth service info: %s", service_info)
            self.set_device_type("RoboMow")
            if service_info.name:
                self.set_device_name(service_info.name.replace("_", " "))
            else:
                self.set_device_name(f"RoboMow {short_address(service_info.address)}")
            return

    @property
    def device_type(self) -> str | None:
        """Return the device type."""
        primary_device_id = self.primary_device_id
        if device_type := self._device_id_to_type.get(primary_device_id):
            return device_type.partition("-")[0]
        return None

    async def async_check_mainboard_serial(
        self,
        hass: HomeAssistant,
        address: str,
        mainboard_serial: str,
    ) -> bool:
        """Set the mainboard serial number and validate it via BLE authentication."""
        client = RoboMowBLEDevice(hass, address, mainboard_serial)
        await client.connect()

        try:
            if not client.is_connected():
                return False

            self._mainboard_serial = mainboard_serial

            for _ in range(10):
                if client.family != MowerFamily.Unknown:
                    break
                await asyncio.sleep(0.1)

            if client.family != MowerFamily.Unknown:
                self.set_device_hw_version(f"{client.mainboard_version}")
                self.set_device_sw_version(
                    f"{client.software_version} ({client.software_release})"
                )
                self.set_device_type(f"RoboMow {client.family.name}")

            return True
        finally:
            await client.disconnect()
