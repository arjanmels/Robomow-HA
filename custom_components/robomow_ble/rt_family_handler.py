"""Compatibility shim for the package RT family handler implementation."""

from __future__ import annotations

import sys
from pathlib import Path

try:
    from robomow_ble.rt_family_handler import RoboMowRtFamilyHandler
except ModuleNotFoundError:
    package_src = (
        Path(__file__).resolve().parents[2] / "packages" / "robomow_ble" / "src"
    )
    if str(package_src) not in sys.path:
        sys.path.insert(0, str(package_src))
    from robomow_ble.rt_family_handler import RoboMowRtFamilyHandler

__all__ = ["RoboMowRtFamilyHandler"]
