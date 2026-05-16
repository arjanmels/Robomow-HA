"""Compatibility shim for the package BLE handler implementation."""

from __future__ import annotations

from robomow_ble.ble_handler import PendingCommand, RoboMowDevice, RoboMowUpdate

__all__ = ["PendingCommand", "RoboMowDevice", "RoboMowUpdate"]
