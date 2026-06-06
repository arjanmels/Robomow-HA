# Robomow via Bluetooth

[![HACS](https://img.shields.io/badge/HACS-Custom-blue?logo=home-assistant&logoColor=white)](https://hacs.xyz/)
[![Release](https://img.shields.io/github/v/release/arjanmels/Robomow-HA)](https://github.com/arjanmels/Robomow-HA/releases/latest)
[![License](https://img.shields.io/github/license/arjanmels/Robomow-HA)](https://github.com/arjanmels/Robomow-HA/blob/main/LICENSE)

Home Assistant integration for Robomow lawnmowers using Bluetooth Low Energy (BLE).
It uses BLE proxies to connect to your Robomow device and provides
real-time status updates.

Currently only supports Robomow RT models.

## Features

- Discover and connect to Robomow devices over BLE
- Lawn mower entity with current state (mowing, charging, docked, etc.) and
  controls to start/stop mowing
- Real-time status sensors for battery, charging, mowing, docked state, and
  errors
- Services to start/stop mowing, return to dock, and set the mowing schedule
- Configuration via UI with device discovery and mainboard serial number input

## Requirements

- Home Assistant `2026.5.0` or newer
- A Robomow lawn mower with Bluetooth support (currently RT models)
- Bluetooth connectivity (direct or via BLE proxy)
- HACS (recommended) or manual installation

## Installation

### HACS Installation (recommended)

1. Open Home Assistant and go to `HACS` > `Integrations`.
2. Click the three-dot menu in the top right and select `Custom repositories`.
3. Add the repository URL:
   `https://github.com/arjanmels/Robomow-HA`
4. Set the repository type to `Integration`.
5. Save, then search for `Robomow via Bluetooth` in HACS and install it.
6. Restart Home Assistant.

### Manual Installation

1. Copy the `custom_components/robomow_ble` directory into
   the `custom_components` directory of your Home Assistant configuration.
2. Restart Home Assistant.

## Configuration

1. In Home Assistant, go to `Settings` > `Devices & Services`.
2. Click `Add Integration`.
3. Search for `Robomow via Bluetooth` and follow the setup flow.
4. Select the available Robomow device discovered via Bluetooth.
5. Enter the mainboard serial number of your Robomow device.
6. Complete the setup and wait for the integration to initialize.

## Obtaining the Mainboard Serial Number

The mainboard serial number is required for authentication with the Robomow
device. You can obtain it by:

1) Log in to `myrobomow.robomow.com`.
2) Open your browser's Developer Tools (F12).
3) Go to the Network tab.
4) Reload the page.
5) Look for a request ending in /api/customer/products.
6) Click the request and open the Response tab.
7) In the JSON response, find the field named `MainboardSerial`.
   That value is the actual mainboard serial number.

## Usage

After setup, the integration will create entities for your Robomow device.
Typical entities include:

- Lawn mower entity with controls to start/stop mowing
- Battery level
- Charging state
- Mowing state
- Docked status
- Error or warning state

You can use these entities in automations, dashboards, and scripts.

Also two services are available:

- `robomow_ble.start_mowing`: Start the mower.
- `robomow_ble.set_mowing_schedule`: Set the mowing schedule.

## Support

If you find a bug or need help, please open an issue at
[https://github.com/arjanmels/Robomow-HA/issues](https://github.com/arjanmels/Robomow-HA/issues)

## Contributing

Contributions are welcome! Please review `CONTRIBUTING.md` before submitting
changes.

## Links

- GitHub repository: `https://github.com/arjanmels/Robomow-HA`
- Issue tracker: `https://github.com/arjanmels/Robomow-HA/issues`
- Robomow BLE library: `https://github.com/arjanmels/Robomow_ble`
