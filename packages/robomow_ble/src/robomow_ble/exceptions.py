"""Package-specific exception types for RoboMow BLE protocol handling."""


class RobomowProtocolError(Exception):
    """Base protocol error."""


class RobomowAuthenticationError(RobomowProtocolError):
    """Raised when BLE authentication fails."""
