"""BLE device data structures for the Robomow integration."""

from __future__ import annotations

import asyncio
import struct
from collections import deque
from contextlib import suppress
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, ClassVar, NamedTuple

from bleak.exc import (
    BleakCharacteristicNotFoundError,
    BleakDeviceNotFoundError,
    BleakError,
)
from bleak_retry_connector import (
    BleakClientWithServiceCache,
    establish_connection,
)

# NOTE: this module still depends on Home Assistant Bluetooth helpers.
from homeassistant.components.bluetooth import async_ble_device_from_address
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.event import async_track_time_interval

from custom_components.robomow_ble.messages import MessageRK, MessageRT

# TODO(AM): child-lock fix, starting zone (reverse engineer), manual mowing, program, next departure, previous departure, status message fix?, error report
# TODO(AM): internationalization
# TODO(AM): split into RT/RX seperate classes with a base class for the generic message handling and state management, or even separate files for messages vs device state management
# TODO(AM): split this file into multiple for better organization
from .ble_consts import (
    AUTH_RESPONSE_LENGTH,
    MESSAGE_RECEIVE_BYTE,
    MESSAGE_SEND_BYTE,
    MESSAGE_START_BYTE,
    MINIMUM_MESSAGE_LENGTH,
    UUID_CHAR_AUTHENTICATE,
    UUID_CHAR_DATA_IN,
    UUID_CHAR_DATA_OUT,
    EepromParam,
    MessageType,
    MessageTypeMisc,
    OperationType,
    WireSignalType,
)
from .const import (
    LOGGER,
    UNKNOWN_FIELD_VALUE,
    UUID_SERVICE,
    EntityKey,
    MowerFamily,
    MowerModel,
    MowerOperatingState,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any

    from bleak.backends.characteristic import BleakGATTCharacteristic
    from bleak.backends.service import BleakGATTService
    from homeassistant.components.bluetooth import (
        BluetoothServiceInfoBleak as BluetoothServiceInfo,
    )
    from homeassistant.core import HomeAssistant


class RoboMowUpdate(NamedTuple):
    """Structured update payload for entity state changes."""

    key: EntityKey
    value: Any


if TYPE_CHECKING:
    type RoboMowUpdateCallback = Callable[[RoboMowUpdate], None]


RESPONSE_COMMAND_COUNTER_SIZE = 2
GET_CONFIG_PAYLOAD_MIN_SIZE = 5
GET_STATUS_PAYLOAD_SIZE = 7
READ_EEPROM_PAYLOAD_SIZE = 4
INFO_PAYLOAD_SIZE = 5
MISC_TYPE_SIZE = 2
ROBOT_STATE_PAYLOAD_MIN_SIZE = 17
MESSAGE_TYPE_STOP_ID_MASK = 0x2


class PendingCommand(NamedTuple):
    """Command metadata kept in the pending-response FIFO queue."""

    counter: int
    msg_type: MessageType
    payload: bytes


class RoboMowDevice:
    """Representation of a Robomow BLE device."""

    def __init__(
        self,
        hass: HomeAssistant,
        address: str,
        mainboard_serial: str,
        update_callback: RoboMowUpdateCallback | None,
    ) -> None:
        """Initialize the device."""
        self._hass: HomeAssistant = hass
        self._address: str = address
        self._mainboard_serial: bytes = (
            mainboard_serial.strip().encode("utf-8") + b"\x00"
        )
        self._update_callback: RoboMowUpdateCallback | None = update_callback

        self._client: BleakClientWithServiceCache | None = None
        self._service: BleakGATTService | None = None
        self._char_auth: BleakGATTCharacteristic | None = None
        self._char_data_in: BleakGATTCharacteristic | None = None
        self._char_data_out: BleakGATTCharacteristic | None = None
        self._command_counter: int = 0
        self._pending_commands: deque[PendingCommand] = deque()
        self._receive_buffer: bytearray = bytearray()
        self._connect_lock = asyncio.Lock()
        self._connect_task_lock = asyncio.Lock()
        self._connect_task: asyncio.Task[None] | None = None
        self._date_time_poll_cancel: Callable[[], None] | None = None
        self._status_poll_cancel: Callable[[], None] | None = None

        self._family: MowerFamily | None = None
        self._model: MowerModel | None = None
        self._software_version: int | None = None
        self._software_release: int | None = None
        self._mainboard_version: int | None = None
        self._program_enabled: bool | None = None
        self._message: str | None = None
        self._operating_state: MowerOperatingState | str | None = None
        self._battery_level: int | None = None
        self._rssi: int | None = None
        self._next_departure: int | None = None
        self._previous_departure: int | None = None
        self._expected_duration: int | None = None
        self._no_depart_reason: str | None = None
        self._anti_theft_enabled: bool | None = None
        self._child_lock_enabled: bool | None = None
        self._anti_theft_active: bool | None = None
        self._mower_home: bool | None = None
        self._charging_active: bool | None = None
        self._disabling_device_removed: bool | None = None
        self._wire_signal_type: int | None = None
        self._starting_point_a: int | None = None
        self._starting_point_b: int | None = None

    # --- State listeners ---

    def _data_changed(self, entity_key: EntityKey, value: Any) -> None:
        """Notify listeners that the mower data has changed."""
        if self._update_callback is not None:
            self._update_callback(RoboMowUpdate(entity_key, value))

    def _set_program_enabled(self, enabled: bool | None) -> None:  # noqa: FBT001
        """Update program_enabled and emit change callbacks when needed."""
        if self._program_enabled == enabled:
            return
        self._program_enabled = enabled
        self._data_changed(EntityKey.PROGRAM_ENABLED, enabled)

    def _set_anti_theft_enabled(self, enabled: bool | None) -> None:  # noqa: FBT001
        """Update anti_theft_enabled and emit change callbacks when needed."""
        if self._anti_theft_enabled == enabled:
            return
        self._anti_theft_enabled = enabled
        self._data_changed(EntityKey.ANTI_THEFT_ENABLED, enabled)

    def _set_child_lock_enabled(self, enabled: bool | None) -> None:  # noqa: FBT001
        """Update child_lock_enabled and emit change callbacks when needed."""
        if self._child_lock_enabled == enabled:
            return
        self._child_lock_enabled = enabled
        self._data_changed(EntityKey.CHILD_LOCK_ENABLED, enabled)

    def _set_anti_theft_active(self, active: bool | None) -> None:  # noqa: FBT001
        """Update anti_theft_active and emit change callbacks when needed."""
        if self._anti_theft_active == active:
            return
        self._anti_theft_active = active
        self._data_changed(EntityKey.ANTI_THEFT_ACTIVE, active)

    def _set_mower_home(self, is_home: bool | None) -> None:  # noqa: FBT001
        """Update mower_home and emit change callbacks when needed."""
        if self._mower_home == is_home:
            return
        self._mower_home = is_home
        self._data_changed(EntityKey.MOWER_HOME, is_home)

    def _set_charging_active(self, active: bool | None) -> None:  # noqa: FBT001
        """Update charging_active and emit change callbacks when needed."""
        if self._charging_active == active:
            return
        self._charging_active = active
        self._data_changed(EntityKey.CHARGING_ACTIVE, active)

    def _set_disabling_device_removed(self, removed: bool | None) -> None:  # noqa: FBT001
        """Update disabling_device_removed and emit change callbacks when needed."""
        if self._disabling_device_removed == removed:
            return
        self._disabling_device_removed = removed
        self._data_changed(EntityKey.DISABLING_DEVICE_REMOVED, removed)

    def _set_wire_signal_type(self, wire_signal_type: int | None) -> None:
        """Update wire signal type and emit change callbacks when needed."""
        if self._wire_signal_type == wire_signal_type:
            return
        self._wire_signal_type = wire_signal_type
        self._data_changed(EntityKey.WIRE_SIGNAL_TYPE, wire_signal_type)

    def _set_starting_point_a(self, value: int | None) -> None:
        """Update starting point A and emit change callbacks when needed."""
        if self._starting_point_a == value:
            return
        self._starting_point_a = value
        self._data_changed(EntityKey.STARTING_POINT_A, value)

    def _set_starting_point_b(self, value: int | None) -> None:
        """Update starting point B and emit change callbacks when needed."""
        if self._starting_point_b == value:
            return
        self._starting_point_b = value
        self._data_changed(EntityKey.STARTING_POINT_B, value)

    # NOTE: user message clearing behavior is not implemented yet.
    def _set_message(self, message: str | None) -> None:
        """Update message text and emit change callbacks when needed."""
        if self._message == message:
            return
        self._message = message
        self._data_changed(EntityKey.MESSAGE, message)

    def _set_state(self, operating_state: MowerOperatingState | str | None) -> None:
        """Update operating state text and emit change callbacks when needed."""
        if self._operating_state == operating_state:
            return
        self._operating_state = operating_state
        self._data_changed(EntityKey.STATE, operating_state)

    def _set_rssi(self, rssi: int | None) -> None:
        """Update RSSI value and emit change callbacks when needed."""
        if self._rssi == rssi:
            return
        self._rssi = rssi
        self._data_changed(EntityKey.SIGNAL_STRENGTH, rssi)

    def _set_battery_level(self, battery_level: int | None) -> None:
        """Update battery level when it changes."""
        if self._battery_level == battery_level:
            return
        self._battery_level = battery_level
        self._data_changed(EntityKey.BATTERY_LEVEL, battery_level)

    def _set_next_departure(self, value: int | None) -> None:
        """Update next departure and emit change callbacks when needed."""
        if self._next_departure == value:
            return
        if value == UNKNOWN_FIELD_VALUE:
            self._next_departure = None
        else:
            self._next_departure = value
        self._data_changed(EntityKey.NEXT_DEPARTURE, self._next_departure)

    def _set_previous_departure(self, value: int | None) -> None:
        """Update previous departure and emit change callbacks when needed."""
        if self._previous_departure == value:
            return
        if value == UNKNOWN_FIELD_VALUE:
            self._previous_departure = None
        else:
            self._previous_departure = value
        self._data_changed(EntityKey.PREVIOUS_DEPARTURE, self._previous_departure)

    def _set_expected_duration(self, value: int | None) -> None:
        """Update expected duration and emit change callbacks when needed."""
        if self._expected_duration == value:
            return
        self._expected_duration = value
        self._data_changed(EntityKey.EXPECTED_DURATION, self._expected_duration)

    def _set_no_depart_reason(self, value: str | None) -> None:
        """Update no-depart reason and emit change callbacks when needed."""
        if self._no_depart_reason == value:
            return
        self._no_depart_reason = value
        self._data_changed(EntityKey.NO_DEPART_REASON, value)

    def _set_family(self, value: MowerFamily | int | None) -> None:
        """Update mower family and emit change callbacks when needed."""
        family = None if value is None else MowerFamily(value)
        if self._family == family:
            return
        self._family = family
        self._data_changed(EntityKey.FAMILY, self._family)

    def _set_model(self, value: MowerModel | int | None) -> None:
        """Update mower model and emit change callbacks when needed."""
        model = None if value is None else MowerModel(value)
        if self._model == model:
            return
        self._model = model
        # Model changes may imply a family change, so update both.
        self._data_changed(EntityKey.MODEL, self._model)

    def _set_software_version(self, value: int | None) -> None:
        """Update software version and emit change callbacks when needed."""
        if self._software_version == value:
            return
        self._software_version = value
        self._data_changed(EntityKey.SOFTWARE_VERSION, self._software_version)

    def _set_software_release(self, value: int | None) -> None:
        """Update software release and emit change callbacks when needed."""
        if self._software_release == value:
            return
        self._software_release = value
        self._data_changed(EntityKey.SOFTWARE_RELEASE, self._software_release)

    def _set_mainboard_version(self, value: int | None) -> None:
        """Update mainboard version and emit change callbacks when needed."""
        if self._mainboard_version == value:
            return
        self._mainboard_version = value
        self._data_changed(EntityKey.MAINBOARD_VERSION, self._mainboard_version)

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
        self._set_message(None)
        self._set_state(None)
        self._set_battery_level(None)
        self._set_program_enabled(None)
        self._set_rssi(None)
        self._set_next_departure(None)
        self._set_previous_departure(None)
        self._set_expected_duration(None)
        self._set_no_depart_reason(None)
        self._set_anti_theft_enabled(None)
        self._set_child_lock_enabled(None)
        self._set_anti_theft_active(None)
        self._set_mower_home(None)
        self._set_charging_active(None)
        self._set_disabling_device_removed(None)
        self._set_wire_signal_type(None)
        self._set_starting_point_a(None)
        self._set_starting_point_b(None)

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

    @property
    def model(self) -> MowerModel:
        """Return the mower model, if known."""
        return self._model or MowerModel.Unknown

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
    def anti_theft_enabled(self) -> bool | None:
        """Return whether anti-theft is enabled, if known."""
        return self._anti_theft_enabled

    @property
    def child_lock_enabled(self) -> bool | None:
        """Return whether child lock is enabled, if known."""
        return self._child_lock_enabled

    @property
    def anti_theft_active(self) -> bool | None:
        """Return whether anti-theft is currently active, if known."""
        return self._anti_theft_active

    @property
    def mower_home(self) -> bool | None:
        """Return whether mower is currently at home, if known."""
        return self._mower_home

    @property
    def charging_active(self) -> bool | None:
        """Return whether charging is currently active, if known."""
        return self._charging_active

    @property
    def status(self) -> str | None:
        """Return the latest mower status text, if known."""
        return self._message

    @property
    def operating_state(self) -> MowerOperatingState | str | None:
        """Return the latest mower operating state text, if known."""
        return self._operating_state

    @property
    def battery_level(self) -> int | None:
        """Return the latest battery level percentage, if known."""
        return self._battery_level

    @property
    def next_departure(self) -> int | None:
        """Return the next scheduled departure time, if known."""
        return self._next_departure

    @property
    def previous_departure(self) -> int | None:
        """Return the previous departure time, if known."""
        return self._previous_departure

    @property
    def expected_duration(self) -> int | None:
        """Return the expected mowing duration, if known."""
        return self._expected_duration

    @property
    def no_depart_reason(self) -> str | None:
        """Return the reason the mower has not departed, if known."""
        return self._no_depart_reason

    @property
    def rssi(self) -> int | None:
        """Return the latest RSSI value, if known."""
        return self._rssi

    def is_connected(self) -> bool:
        """Return True if the client is connected."""
        return self._client is not None and self._client.is_connected

    # --- Connection lifecycle ---

    async def _connect_worker(self) -> None:
        """Perform a single serialized connect attempt."""
        async with self._connect_lock:
            if self._client is not None and self._client.is_connected:
                LOGGER.debug("BLE client already connected")
                return

            LOGGER.debug("Connecting to Robomow BLE device")

            try:
                await self._establish_client_connection()
                self._resolve_characteristics()
                await self._authenticate_connection()
                await self._start_notifications()
            except BleakError:
                await self._disconnect_unlocked()
                raise

            self._initialize_runtime_state()

            # Start periodic date/time updates
            self._start_date_time_polling()

            # Start periodic GET_STATUS polling
            self._start_status_polling()

            await self._send_msg(MessageType.GET_CONFIG)
            await self._send_msg(MessageType.GET_MESSAGE)
            await self._send_misc_msg(MessageTypeMisc.INFO)

            await self._read_eeprom_param(
                EepromParam.CHILD_LOCK_ENABLED,
                EepromParam.ANTI_THEFT_ENABLED,
                EepromParam.PROGRAM_ENABLED,
                EepromParam.WIRE_SIGNAL_TYPE,
                EepromParam.STARTING_POINT_A,
                EepromParam.STARTING_POINT_B,
            )

    async def connect(self) -> None:
        """Create and connect a Robomow BLE client."""
        async with self._connect_task_lock:
            if self._connect_task is None or self._connect_task.done():
                self._connect_task = self._hass.async_create_task(
                    self._connect_worker()
                )
            connect_task = self._connect_task

        await connect_task

    async def _disconnect_unlocked(self) -> None:
        """Disconnect without acquiring the connect lock."""
        LOGGER.debug("BLE client disconnect called")
        self._cancel_periodic_polling()
        if self._client is not None and self._client.is_connected:
            if self._char_data_in is not None:
                await self._client.stop_notify(self._char_data_in)
            await self._client.disconnect()

    async def disconnect(self) -> None:
        """Disconnect the BLE client."""
        async with self._connect_task_lock:
            connect_task = self._connect_task
            self._connect_task = None

        if connect_task is not None and not connect_task.done():
            connect_task.cancel()
            with suppress(asyncio.CancelledError):
                await connect_task

        async with self._connect_lock:
            await self._disconnect_unlocked()

    # --- Packet I/O ---

    async def _write_value(self, data: bytes) -> bool:
        """Write a packet payload to the mower data output characteristic."""
        if not self.is_connected() or not self._client or not self._char_data_out:
            return False

        try:
            await self._client.write_gatt_char(self._char_data_out, data, response=True)
        except BleakError as err:
            LOGGER.error("Error writing data: %s", err)
            return False
        return True

    @staticmethod
    def _calculate_checksum(data: bytes) -> int:
        """Calculate packet checksum by XORing 0xFF with the byte sum."""
        return (~sum(data)) & 0xFF

    async def _send_msg(
        self, msg_type: MessageType, payload: bytes | None = None
    ) -> bool:
        """Update packet checksum and write it to the BLE characteristic."""
        payload = payload or b""

        LOGGER.debug("Sending  %-15s: %s", msg_type.name, payload.hex())

        packet = struct.pack(
            ">BBBB", MESSAGE_START_BYTE, 5 + len(payload), MESSAGE_SEND_BYTE, msg_type
        )
        packet += payload
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
            with suppress(ValueError):
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
        await self._send_msg(MessageType.GET_MESSAGE)
        await self._send_misc_msg(MessageTypeMisc.STATE)
        await self._read_eeprom_param(
            EepromParam.CHILD_LOCK_ENABLED,
            EepromParam.ANTI_THEFT_ENABLED,
            EepromParam.PROGRAM_ENABLED,
            EepromParam.WIRE_SIGNAL_TYPE,
            EepromParam.STARTING_POINT_A,
            EepromParam.STARTING_POINT_B,
        )

    # --- EEPROM / commands ---

    async def _read_eeprom_param(self, *params: EepromParam) -> bool:
        """Send a message to read one or more EEPROM parameters by ID."""
        if not params:
            return False

        payload = struct.pack(
            f">{len(params)}H",
            *(int(param) for param in params),
        )
        return await self._send_msg_with_sequence(MessageType.READ_EEPROM, payload)

    async def _write_eeprom_param(self, param: EepromParam, value: int) -> bool:
        """Send a message to write an EEPROM parameter with the given ID and value."""
        return await self._send_msg_with_sequence(
            MessageType.WRITE_EEPROM, struct.pack(">HL", param, value)
        )

    async def enable_program(self) -> None:
        """Send a message to enable the mower program."""
        await self._write_eeprom_param(EepromParam.PROGRAM_ENABLED, 1)
        await self._send_misc_msg(MessageTypeMisc.STATE)

    async def disable_program(self) -> None:
        """Send a message to disable the mower program."""
        await self._write_eeprom_param(EepromParam.PROGRAM_ENABLED, 0)
        await self._send_misc_msg(MessageTypeMisc.STATE)

    async def enable_anti_theft(self) -> None:
        """Enable anti-theft mode (currently unsupported by protocol mapping)."""
        await self._write_eeprom_param(EepromParam.ANTI_THEFT_ENABLED, 1)
        await self._send_misc_msg(MessageTypeMisc.STATE)

    async def disable_anti_theft(self) -> None:
        """Disable anti-theft mode (currently unsupported by protocol mapping)."""
        await self._write_eeprom_param(EepromParam.ANTI_THEFT_ENABLED, 0)
        await self._send_misc_msg(MessageTypeMisc.STATE)

    async def enable_child_lock(self) -> None:
        """Enable child lock."""
        await self._write_eeprom_param(EepromParam.CHILD_LOCK_ENABLED, 1)
        await self._send_misc_msg(MessageTypeMisc.STATE)
        await self._read_eeprom_param(EepromParam.CHILD_LOCK_ENABLED)

    async def disable_child_lock(self) -> None:
        """Disable child lock."""
        await self._write_eeprom_param(EepromParam.CHILD_LOCK_ENABLED, 0)
        await self._send_misc_msg(MessageTypeMisc.STATE)
        await self._read_eeprom_param(EepromParam.CHILD_LOCK_ENABLED)

    async def set_wire_signal_type(self, wire_signal_type: WireSignalType) -> None:
        """Set wire signal type and refresh it from EEPROM."""
        await self._write_eeprom_param(
            EepromParam.WIRE_SIGNAL_TYPE, int(wire_signal_type)
        )
        await self._read_eeprom_param(EepromParam.WIRE_SIGNAL_TYPE)

    async def set_starting_point_a(self, value: int) -> None:
        """Set starting point A and refresh it from EEPROM."""
        await self._write_eeprom_param(EepromParam.STARTING_POINT_A, value)
        await self._read_eeprom_param(EepromParam.STARTING_POINT_A)

    async def set_starting_point_b(self, value: int) -> None:
        """Set starting point B and refresh it from EEPROM."""
        await self._write_eeprom_param(EepromParam.STARTING_POINT_B, value)
        await self._read_eeprom_param(EepromParam.STARTING_POINT_B)

    async def start_mowing(
        self,
        duration_minutes: int | None = None,
        starting_zone: int | None = None,
    ) -> None:
        """Send a message to start the mower program, optionally with a duration."""
        duration_minutes = (
            max(1, min(0xFF, duration_minutes)) if duration_minutes is not None else 30
        )
        starting_zone = (
            max(0, min(0xFF, starting_zone)) if starting_zone is not None else 0x80
        )
        await self._send_msg_with_sequence(
            MessageType.COMMAND,
            struct.pack(
                ">BBB",
                OperationType.START_MOWING,
                starting_zone,
                duration_minutes,
            ),
        )
        await self._send_msg(MessageType.GET_MESSAGE)
        await self._send_misc_msg(MessageTypeMisc.STATE)

    async def start_mowing_edge(self) -> None:
        """Send a message to start edge mowing."""
        await self._send_msg_with_sequence(
            MessageType.COMMAND,
            struct.pack(">BB", OperationType.START_EDGE_MOWING, 0x80),
        )
        await self._send_msg(MessageType.GET_MESSAGE)
        await self._send_misc_msg(MessageTypeMisc.STATE)

    async def stop_mowing(self) -> None:
        """Send a message to stop the mower program."""
        await self._send_msg_with_sequence(
            MessageType.COMMAND, struct.pack(">BB", OperationType.STOP_MOWING, 0xFF)
        )
        await self._send_msg(MessageType.GET_MESSAGE)
        await self._send_misc_msg(MessageTypeMisc.STATE)

    async def return_to_home(self) -> None:
        """Send a message to return the mower to its home base."""
        await self._send_msg_with_sequence(
            MessageType.COMMAND, struct.pack(">BB", OperationType.RETURN_HOME, 0xBF)
        )
        await self._send_msg(MessageType.GET_MESSAGE)
        await self._send_misc_msg(MessageTypeMisc.STATE)

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
                    "Detected %d missing response(s) before command counter 0x%04X: %s",
                    len(skipped),
                    command_counter,
                    ", ".join(f"0x{command.counter:04X}" for command in skipped),
                )

            cmd = self._pending_commands.popleft()
            if msg_type not in (MessageType.ACKNOWLEDGE, cmd.msg_type):
                LOGGER.warning(
                    "Expected response of type %s for command counter 0x%04X but got "
                    "type %s",
                    cmd.msg_type.name,
                    command_counter,
                    msg_type.name,
                )
                return None
            return cmd

        return None

    # --- BLE event handlers ---

    def _handle_disconnect(self, _client: BleakClientWithServiceCache) -> None:
        """Handle BLE disconnect callback."""
        LOGGER.debug("BLE client disconnected")
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
                    "Received malformed packet: %s",
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
                    "Received packet with invalid checksum: %s",
                    packet.hex(),
                )
                continue

            try:
                msg_type = MessageType(packet[3])
            except ValueError:
                LOGGER.warning(
                    "Received packet with unknown msg_type 0x%02X: %s",
                    packet[3],
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
        LOGGER.debug("Received %-15s: %s", msg_type.name, payload.hex())

        if msg_type == MessageType.GET_CONFIG:
            self._handle_get_config(payload)
        elif msg_type == MessageType.GET_MESSAGE:
            self._handle_get_message(payload)
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
            family,
            software_version,
            software_release,
            mainboard_version,
        ) = struct.unpack_from(">BBHB", payload)
        self._set_family(family)
        self._set_software_version(software_version)
        self._set_software_release(software_release)
        self._set_mainboard_version(mainboard_version)
        LOGGER.debug(
            "  CONFIG: family=%s, software_version=%s, "
            "software_release=%s, mainboard_version=%s",
            self.family.name,
            self.software_version,
            self.software_release,
            self.mainboard_version,
        )

    def _handle_get_message(self, payload: bytes) -> None:
        """Handle a GET_STATUS response packet."""
        if not self._check_payload_length(
            MessageType.GET_MESSAGE, payload, GET_STATUS_PAYLOAD_SIZE, exact=True
        ):
            return

        (msgtype, msgid, stopid, _failureid) = struct.unpack_from(">BHHH", payload)

        if msgtype & MESSAGE_TYPE_STOP_ID_MASK:
            message = (
                ""
                if stopid == UNKNOWN_FIELD_VALUE
                else MessageRK.get_stop_message(stopid)
            )
            self._set_message("Error: " + str(message))
        else:
            message = (
                "" if msgid == UNKNOWN_FIELD_VALUE else MessageRK.get_message(msgid)
            )
            self._set_message(str(message))

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
                "Received %s response with unknown command counter 0x%04X",
                msg_type.name,
                command_counter,
            )
            return

        if msg_type == MessageType.READ_EEPROM:
            self._handle_read_eeprom_response(request, response)
        elif msg_type == MessageType.MISCELLANEOUS:
            self._handle_miscellaneous_response(request, response)
        elif msg_type == MessageType.ACKNOWLEDGE:
            pass  # No additional handling needed for ACKNOWLEDGE responses
        else:
            LOGGER.warning(
                "Received %s response with unhandled msg_type for command counter "
                "0x%04X: %s => %s",
                request.msg_type.name,
                command_counter,
                request.payload.hex(),
                response.payload.hex(),
            )

    def _handle_read_eeprom_response(
        self, request: PendingCommand, response: PendingCommand
    ) -> None:
        """Handle a READ_EEPROM response after the pending command has been matched."""
        if not self._check_payload_length(
            MessageType.READ_EEPROM,
            response.payload,
            READ_EEPROM_PAYLOAD_SIZE * len(request.payload) // 2,
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
                ">L", response.payload, offset=index * READ_EEPROM_PAYLOAD_SIZE
            )[0]

            try:
                field_name = EepromParam(field).name
            except ValueError:
                field_name = f"0x{field:04X}"

            LOGGER.debug(
                "  EEPROM: %s=0x%08X",
                field_name,
                value,
            )

            if field == EepromParam.WIRE_SIGNAL_TYPE:
                self._set_wire_signal_type(value)
            elif field == EepromParam.STARTING_POINT_A:
                self._set_starting_point_a(value)
            elif field == EepromParam.STARTING_POINT_B:
                self._set_starting_point_b(value)

    _AUTOMATIC_OPERATION_LABELS: ClassVar[dict[int, MowerOperatingState]] = {
        0: MowerOperatingState.WARMING_UP,
        1: MowerOperatingState.GOING_TO_START,
        2: MowerOperatingState.MOWING,
        3: MowerOperatingState.EDGE_MOWING,
        4: MowerOperatingState.RETURNING_HOME_WARMING_UP,
        5: MowerOperatingState.RETURNING_HOME_FOLLOWING_EDGE,
        6: MowerOperatingState.RETURNING_HOME_SEARCHING_EDGE,
        7: MowerOperatingState.LEARNING_ENTRY_POINT,
    }

    _OPERATING_STATE_AUTOMATIC: ClassVar[int] = 3

    _OPERATING_STATE_LABELS: ClassVar[dict[int, MowerOperatingState]] = {
        1: MowerOperatingState.IDLE,
        2: MowerOperatingState.CHARGING,
        _OPERATING_STATE_AUTOMATIC: MowerOperatingState.AUTOMATIC,
        4: MowerOperatingState.REMOTE_CONTROL,
        5: MowerOperatingState.BIT,
    }

    STATE_LABELS: ClassVar[list[str]] = [
        *(state.value for state in _OPERATING_STATE_LABELS.values()),
        *(state.value for state in _AUTOMATIC_OPERATION_LABELS.values()),
    ]

    def _describe_operating_state(
        self, state: int, operation: int
    ) -> MowerOperatingState | str:
        """Return human-readable text for the mower operating state."""
        if state == self._OPERATING_STATE_AUTOMATIC:
            return self._AUTOMATIC_OPERATION_LABELS.get(
                operation, f"Unknown Automatic ({operation})"
            )
        return self._OPERATING_STATE_LABELS.get(state, f"Unknown ({state})")

    def _handle_miscellaneous_response(
        self, request: PendingCommand, response: PendingCommand
    ) -> None:
        """Handle a MISCELLANEOUS response after matching the pending command."""
        if not self._check_payload_length(
            MessageType.MISCELLANEOUS, response.payload, MISC_TYPE_SIZE
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
            if not self._check_payload_length(
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
                one_time_setup,
                no_depart_reason,
                byte_10,
                byte_11,
                byte_12,
                charging_state,
            ) = struct.unpack_from(
                ">BBBHHBBBBBBB", response.payload, offset=MISC_TYPE_SIZE
            )

            operation = byte_0 & 0x07
            bit_0_3 = byte_0 & 0x08 != 0
            program_enabled = byte_0 & 0x10 != 0

            anti_theft_enabled = byte_10 & 0x01 != 0
            anti_theft_active = byte_10 & 0x02 != 0
            bit_10_3 = byte_10 & 0x04 != 0  # NOTE: maybe error or ready flag?
            bit_10_4 = byte_10 & 0x08 != 0
            child_lock_enabled = byte_10 & 0x10 != 0

            mower_home = byte_11 & 0x01 != 0
            disabling_device_removed = byte_11 & 0x02 != 0
            energy_saving_mode = byte_11 & 0x04 != 0
            bit_11_2 = byte_11 & 0x08 != 0
            charging_active = byte_11 & 0x10 != 0
            bit_11_5_to_6 = (byte_11 & 0x60) >> 5

            LOGGER.debug(
                "  ROBOT_STATE:"
                "\n  "
                "byte_0=0x%02X, "
                "operation=0x%02X, "
                "bit_0_3=%s, "
                "program_enabled=%s, "
                "state=%02X, "
                "battery_level=%s, "
                "next_departure=%s, "
                "previous_departure=%s, "
                "expected_duration=%s, "
                "one_time_setup=%s, "
                "no_depart_reason=%s, "
                "\n  "
                "byte_10=0x%02X, "
                "anti_theft_enabled=%s, "
                "anti_theft_active=%s, "
                "bit_10_3=%s, "
                "bit_10_4=%s, "
                "child_lock_enabled=%s, "
                "byte_11=0x%02X, "
                "mower_home=%s, "
                "disabling_device_removed=%s, "
                "energy_saving_mode=%s, "
                "bit_11_2=%s, "
                "charging_active=%s, "
                "bit_11_5_to_6=%s, "
                "byte_12=0x%02X, "
                "charging_state=%02X, ",
                byte_0,
                operation,
                bit_0_3,
                program_enabled,
                state,
                battery_level,
                next_departure,
                previous_departure,
                expected_duration,
                one_time_setup,
                no_depart_reason,
                byte_10,
                anti_theft_enabled,
                anti_theft_active,
                bit_10_3,
                bit_10_4,
                child_lock_enabled,
                byte_11,
                mower_home,
                disabling_device_removed,
                energy_saving_mode,
                bit_11_2,
                charging_active,
                bit_11_5_to_6,
                byte_12,
                charging_state,
            )

            self._set_program_enabled(program_enabled)
            self._set_anti_theft_enabled(anti_theft_enabled)
            self._set_child_lock_enabled(child_lock_enabled)
            self._set_anti_theft_active(anti_theft_active)
            self._set_mower_home(mower_home)
            self._set_charging_active(charging_active)
            self._set_disabling_device_removed(disabling_device_removed)
            self._set_state(self._describe_operating_state(state, operation))
            self._set_battery_level(battery_level)
            self._set_next_departure(next_departure)
            self._set_previous_departure(previous_departure)
            self._set_expected_duration(expected_duration)
            self._set_no_depart_reason(
                ""
                if no_depart_reason == 0
                else str(MessageRT.get_message(no_depart_reason))
            )
        elif misc_type == MessageTypeMisc.INFO:
            if not self._check_payload_length(
                MessageType.MISCELLANEOUS,
                response.payload,
                INFO_PAYLOAD_SIZE,
                exact=True,
            ):
                return

            model, max_cycles, max_areas = struct.unpack_from(
                ">BBB", response.payload, offset=MISC_TYPE_SIZE
            )
            self._set_model(model)

            LOGGER.debug(
                "  INFO: model=%s (%d), max_cycles=%d, max_areas=%d",
                self._model.name if self._model else "Unknown",
                model,
                max_cycles,
                max_areas,
            )

    def update_from_service_info(self, service_info: BluetoothServiceInfo) -> None:
        """Update from BLE service info."""
        LOGGER.debug(
            "Processing Bluetooth service info (update_from_service_info): %s",
            service_info,
        )
        self._set_rssi(service_info.rssi)
