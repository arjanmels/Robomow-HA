"""Config flow for Robomow via Bluetooth integration."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

import voluptuous as vol
from bleak.exc import (
    BleakCharacteristicNotFoundError,
    BleakDeviceNotFoundError,
)
from bluetooth_data_tools import short_address
from bluetooth_sensor_state_data import BluetoothData
from homeassistant.components.bluetooth import (
    BluetoothServiceInfo,
    BluetoothServiceInfoBleak,
    async_ble_device_from_address,
    async_discovered_service_info,
)
from homeassistant.config_entries import ConfigFlow
from homeassistant.const import CONF_ADDRESS
from homeassistant.exceptions import (
    ConditionError,
    ConfigEntryAuthFailed,
)
from robomow_ble import RobomowAuthenticationError, RobomowDevice

from .const import (
    CONF_DEVICE_TYPE,
    CONF_MAINBOARD_SERIAL,
    DOMAIN,
    LOGGER,
    UUID_SERVICE,
    MowerModel,
)

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigFlowResult
    from homeassistant.core import HomeAssistant


class RobomowBLEConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Robomow BLE."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize config flow instance state."""
        self._discovery_info: BluetoothServiceInfoBleak | None = None
        self._discovered_device: RobomowConfigData | None = None
        self._discovered_devices: dict[
            str, tuple[RobomowConfigData, BluetoothServiceInfoBleak]
        ] = {}

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> ConfigFlowResult:
        """Handle the bluetooth discovery step."""
        LOGGER.debug("Discovered Bluetooth service info: %s", discovery_info)
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()
        device = RobomowConfigData()
        if not device.supported(discovery_info):
            return self.async_abort(reason="not_supported")
        self._discovery_info = discovery_info
        self._discovered_device = device
        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm discovery."""
        LOGGER.debug("Confirming Bluetooth discovery with user input: %s", user_input)

        device = self._discovered_device
        discovery_info = self._discovery_info

        if device is None or discovery_info is None:
            return self.async_abort(reason="no_devices_found")

        errors: dict[str, str] = {}

        title = device.title or device.get_device_name() or discovery_info.name
        if user_input is not None:
            try:
                await device.async_check_mainboard_serial(
                    hass=self.hass,
                    address=discovery_info.address,
                    mainboard_serial=user_input[CONF_MAINBOARD_SERIAL],
                )
            except BleakDeviceNotFoundError:
                errors[CONF_MAINBOARD_SERIAL] = "device_not_found"
            except BleakCharacteristicNotFoundError:
                errors[CONF_MAINBOARD_SERIAL] = "characteristics_not_found"
            except ConfigEntryAuthFailed:
                errors[CONF_MAINBOARD_SERIAL] = "invalid_mainboard_serial"
            except ConditionError:
                errors[CONF_MAINBOARD_SERIAL] = "model_unsupported"

            if not errors:
                return self.async_create_entry(
                    title=title,
                    data={
                        CONF_DEVICE_TYPE: device.device_type,
                        CONF_MAINBOARD_SERIAL: user_input[CONF_MAINBOARD_SERIAL],
                    },
                )

        self._set_confirm_only()
        return self.async_show_form(
            step_id="bluetooth_confirm",
            description_placeholders={"name": title},
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_MAINBOARD_SERIAL): vol.All(
                        str, vol.Length(min=14, max=14)
                    )
                }
            ),
            errors=errors,
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the user step to pick a discovered device."""
        LOGGER.debug("Handling user step with input: %s", user_input)

        errors: dict[str, str] = {}

        if user_input is not None:
            address = user_input[CONF_ADDRESS]
            await self.async_set_unique_id(address, raise_on_progress=False)
            self._abort_if_unique_id_configured()
            device, discovery_info = self._discovered_devices[address]
            title = device.title or device.get_device_name() or discovery_info.name

            try:
                await device.async_check_mainboard_serial(
                    hass=self.hass,
                    address=discovery_info.address,
                    mainboard_serial=user_input[CONF_MAINBOARD_SERIAL],
                )
            except BleakDeviceNotFoundError:
                errors[CONF_MAINBOARD_SERIAL] = "device_not_found"
            except BleakCharacteristicNotFoundError:
                errors[CONF_MAINBOARD_SERIAL] = "characteristics_not_found"
            except ConfigEntryAuthFailed:
                errors[CONF_MAINBOARD_SERIAL] = "invalid_mainboard_serial"

            if not errors:
                return self.async_create_entry(
                    title=title,
                    data={
                        CONF_DEVICE_TYPE: device.device_type,
                        CONF_MAINBOARD_SERIAL: user_input[CONF_MAINBOARD_SERIAL],
                    },
                )

        current_addresses = self._async_current_ids(include_ignore=False)
        LOGGER.debug("Current configured addresses: %s", current_addresses)

        all_service_infos = async_discovered_service_info(self.hass, connectable=False)

        for discovery_info in all_service_infos:
            address = discovery_info.address
            if address in current_addresses or address in self._discovered_devices:
                continue
            device = RobomowConfigData()
            if device.supported(discovery_info):
                LOGGER.debug("Discovered supported Robomow device: %s", discovery_info)
                self._discovered_devices[address] = (device, discovery_info)

        if not self._discovered_devices:
            return self.async_abort(reason="no_devices_found")

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ADDRESS): vol.In(
                        {
                            address: (
                                f"{device.get_device_name(None) or discovery_info.name}"
                                f" ({address})"
                            )
                            for address, (
                                device,
                                discovery_info,
                            ) in self._discovered_devices.items()
                        }
                    ),
                    vol.Required(CONF_MAINBOARD_SERIAL): vol.All(
                        str, vol.Length(min=14, max=14)
                    ),
                }
            ),
            errors=errors,
        )


class RobomowConfigData(BluetoothData):
    """Data about a Robomow BLE device."""

    def _start_update(self, data: BluetoothServiceInfo) -> None:
        """Update from BLE advertisement data."""
        LOGGER.debug(
            "Processing Bluetooth service info (_start_update): %s",
            data,
        )
        self.set_device_manufacturer("Robomow")
        self.set_device_name(data.name)
        self.set_precision(2)

        if UUID_SERVICE in map(str.lower, data.service_uuids or []):
            LOGGER.debug("Processing Bluetooth service info: %s", data)
            self.set_device_type("Robomow")
            if data.name:
                self.set_device_name(data.name.replace("_", " "))
            else:
                self.set_device_name(f"Robomow {short_address(data.address)}")
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
        mower = RobomowDevice(mainboard_serial, None)
        device = async_ble_device_from_address(hass, address, connectable=True)

        if device is None:
            msg = f"Device with address {address} not found"
            raise BleakDeviceNotFoundError(msg)

        try:
            await mower.async_connect(device)
        except RobomowAuthenticationError as err:
            raise ConfigEntryAuthFailed from err

        try:
            if not mower.is_connected():
                return False

            self._mainboard_serial = mainboard_serial

            for _ in range(10):
                if mower.model is not None:
                    break
                await asyncio.sleep(0.1)

            if mower.model is None:
                raise ConfigEntryAuthFailed

            if mower.model == MowerModel.Unknown:
                msg = "Mower model is unknown"
                raise ConditionError(msg)

            self.set_device_type(f"Robomow {mower.model.name}")
            self.set_device_hw_version(f"{mower.mainboard_version}")
            self.set_device_sw_version(
                f"{mower.software_version} ({mower.software_release})"
            )

            return True
        finally:
            await mower.async_disconnect()
