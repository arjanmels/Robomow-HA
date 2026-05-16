"""Exceptions for Robomow BLE integration."""

from __future__ import annotations


class RoboMowError(Exception):
    """Base exception for Robomow integration."""


class RoboMowAuthenticationError(RoboMowError):
    """Raised when BLE authentication fails."""


class ModelNotSupportedError(RoboMowError):
    """Raised when the mower model is unknown or not supported."""
