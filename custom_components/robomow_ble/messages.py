"""Compatibility shim for package message lookup helpers."""

from __future__ import annotations

import sys
from pathlib import Path

try:
    from robomow_ble.messages import Message, MessageRK, MessageRT
except ModuleNotFoundError:
    package_src = (
        Path(__file__).resolve().parents[2] / "packages" / "robomow_ble" / "src"
    )
    if str(package_src) not in sys.path:
        sys.path.insert(0, str(package_src))
    from robomow_ble.messages import Message, MessageRK, MessageRT

__all__ = ["Message", "MessageRK", "MessageRT"]
