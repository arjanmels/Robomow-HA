"""Config flow for Robomow via Bluetooth integration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import voluptuous as vol
from bleak.exc import (
    BleakCharacteristicNotFoundError,
    BleakDeviceNotFoundError,
)
from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
    async_discovered_service_info,
)
from homeassistant.config_entries import ConfigFlow
from homeassistant.const import CONF_ADDRESS
from homeassistant.exceptions import ConfigEntryAuthFailed

from .ble_handler import RoboMowBLEDeviceData
from .const import CONF_DEVICE_TYPE, CONF_MAINBOARD_SERIAL, DOMAIN, LOGGER

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigFlowResult


class RoboMowBLEConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Robomow BLE."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._discovery_info: BluetoothServiceInfoBleak | None = None
        self._discovered_device: RoboMowBLEDeviceData | None = None
        self._discovered_devices: dict[
            str, tuple[RoboMowBLEDeviceData, BluetoothServiceInfoBleak]
        ] = {}

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> ConfigFlowResult:
        """Handle the bluetooth discovery step."""
        LOGGER.debug("Discovered Bluetooth service info: %s", discovery_info)
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()
        device = RoboMowBLEDeviceData()
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

            title = device.title or device.get_device_name() or discovery_info.name
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
            device = RoboMowBLEDeviceData()
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
