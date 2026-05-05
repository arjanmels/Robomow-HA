# ruff: noqa: E501
"""Message lookup helpers."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "Message",
    "MessageRK",
    "MessageRT",
]


@dataclass(frozen=True)
class Message:
    """Base class for user-facing messages with optional title and text."""

    title: str
    text: str = ""

    def __str__(self) -> str:
        """Return a user-friendly string representation of the message."""
        return f"{self.title} - {self.text}" if self.text else self.title


@dataclass(frozen=True)
class MessageRK(Message):
    """A user-facing message for RK machines."""

    @staticmethod
    def get_message(number: int) -> Message:
        """Get both title and text for machine/message number."""
        return Message(title=RK_TITLES.get(number, f"Unknown message {number}"))

    @staticmethod
    def get_stop_message(number: int) -> Message:
        """Get both title and text for machine/message number."""
        message = RK_STOP_MESSAGES.get(number)
        if message is None:
            return Message(title=f"Unknown stop message {number}")
        return message


@dataclass(frozen=True)
class MessageRT(Message):
    """A user-facing message for RT machines."""

    @staticmethod
    def get_message(number: int) -> Message:
        """Get both title and text for machine/message number."""
        message = RT_MESSAGES.get(number)
        if message is None:
            return Message(title=f"Unknown message {number}")
        return message


RK_TITLES: dict[int, str] = {
    1: "Passed (not in use)",
    2: "Failure",
    3: "Wait…",
    4: "No wire signal",
    5: "Recharge battery",
    6: "Lift was detected",
    7: "Button pressed",
    8: "Low temperature detected",
    9: "Operation time completed",
    10: "Check mowing Height",
    11: "Waiting for power supply",
    12: "Keep charging  if not in use",
    13: "Docking problem detected",
    14: "Please start the operation elsewhere",
    15: "Cross outside",
    16: "Switch perimeter wire connectors",
    17: "Place mower inside lawn to start",
    18: "Stuck In place",
    19: "Did not find Sub Zone 1",
    20: "Did not find Sub Zone 2",
    21: "Did not find Sub Zone 3",
    22: "Did not find Sub Zone 4",
    23: "No base station in this zone",
    24: "Operations shorter than expected",
    25: "Waiting for  wire signal",
    26: "Turn off wire  signal",
    27: "Turn on wire  signal",
    28: "Mowing motor problem",
    29: "Warming Up",
    30: "Press stop at sub zone entry",
    31: "Learn edge distance (not in use)",
    32: "Going to entry point",
    33: "Searching for Base",
    34: "Wire position Test",
    35: "Edge termination Test",
    36: "Near wire follow Test",
    37: "Demo mode",
    38: "Edge (not in use)",
    39: "Scan (not in use)",
    40: "Place mower  in base",
    41: "Antitheft alarm warning(not in use)",
    42: "Mowing motor overheat",
    43: "Mowing motor cooling down",
    44: "activate motors (not in use)",
    45: "place robot on ground (not in use)",
    46: "robot is lifted (not in use)",
    47: "Remove disabling key before lifting",
    48: "Antitheft is operational(not in use)",
    49: "mower docked (not in use)",
    50: "Disabled mode is active",
    51: "Help needed; restart in new location",
    52: "Drive motor overheat",
    53: "Drive motor cooling down",
    54: "Bumper was pressed",
    55: "Help needed; restart in new location",
    56: "Inactive time (not in use)",
    57: "Bumper is presed (not in use)",
    58: "Testing mode: Drive motors activated",
    59: "Testing mode: mow motors activated",
    60: "drive driver problem (not in use)",
    61: "Help needed; restart in new location",
    62: "Help needed; restart in new location",
    63: "Base station pairing required",
    64: "Battery compartment door is open",
    65: "Test mode",
    66: "Cover is opened",
    67: "Place mower in the base station",
}

RK_STOP_MESSAGES: dict[int, Message] = {
    2: Message(
        title="No wire signal",
        text="Make sure the base station is connected to power supply. Disconnect the power supply and reconnect after 10 seconds. Check connection of the perimeter wire to the base station. Check for breaks in the perimeter wire.",
    ),
    3: Message(
        title="Place mower inside lawn to start",
        text="Please restart operation inside the perimeter wire (3)",
    ),
    5: Message(title="Bumper was pressed", text="Bumper pressed"),
    6: Message(
        title="Lift was detected", text="Mower needs your help, please restart (6)"
    ),
    7: Message(
        title="Stuck In place", text="Mower needs your help, please restart (7)"
    ),
    8: Message(
        title="Stuck In place", text="Mower needs your help, please restart (8)"
    ),
    9: Message(
        title="Waiting for power supply",
        text="Robot got off the base station because charging voltage is not detected",
    ),
    10: Message(
        title="Waiting for power supply",
        text="Charging will resume after power supply returns",
    ),
    11: Message(
        title="Waiting for power supply",
        text="Charging will resume after power supply returns",
    ),
    14: Message(
        title="Docking problem detected",
        text="Mower needs your help, place mower in base station and check charging (14)",
    ),
    15: Message(title="Recharge battery", text="Mower needs to be recharged (15)"),
    17: Message(title="Recharge battery", text="Mower needs to be recharged (17)"),
    18: Message(title="Recharge battery", text="Mower needs to be recharged (18)"),
    19: Message(
        title="Waiting for power supply",
        text="Charging process is halted because charger overheat is detected",
    ),
    21: Message(
        title="Failure",
        text="Automatic departure is disabled due to low temperature (21)",
    ),
    22: Message(
        title="Please start the operation elsewhere",
        text="more then 10 drive overcurrent events occurred during scan",
    ),
    23: Message(
        title="Please start the operation elsewhere",
        text="Mower needs your help, please restart (23)",
    ),
    25: Message(
        title="Remove disabling key before lifting",
        text="Mower needs your help, please restart operation  (25)",
    ),
    27: Message(
        title="Mowing motor overheat",
        text="Mow overheat is detected, place mower in base station (27)",
    ),
    28: Message(
        title="Check mowing Height", text="Mower needs your help, please restart (28)"
    ),
    29: Message(
        title="Check mowing Height", text="Mower needs your help, please restart (29)"
    ),
    30: Message(
        title="No wire signal",
        text="Make sure the base station is connected to power supply. Disconnect the power supply and reconnect after 10 seconds. Check connection of the perimeter wire to the base station. Check for breaks in theperimeter wire.",
    ),
    31: Message(
        title="Mowing motor overheat",
        text="Mow overheat is detected during manual operation ",
    ),
    32: Message(
        title="Cross outside",
        text="Please start operation inside the perimeter wire (32)",
    ),
    33: Message(
        title="Lift was detected", text="Mower needs your help, please restart (33)"
    ),
    34: Message(
        title="Inactive time (not in use)",
        text="Returning to base station due to inactive time (34)",
    ),
    35: Message(
        title="Operation time completed",
        text="We reached the required mowing time in the current active zone",
    ),
    37: Message(
        title="Failure",
        text="We are during the BIT edge terminate test and end of edge is detected",
    ),
    38: Message(
        title="Failure",
        text="Remote control Safety button is pressed during automatic operation",
    ),
    39: Message(title="Failure", text="Stop button is pressed during manual operation"),
    41: Message(title="Failure", text="Mower needs your help, please restart (41)"),
    42: Message(
        title="Lift was detected", text="Mower needs your help, please restart (42)"
    ),
    44: Message(
        title="Stuck In place", text="Mower needs your help, please restart (44)"
    ),
    46: Message(
        title="Mowing motor overheat",
        text="Mow Motor overheating has been detected, place mower in base station (46)",
    ),
    47: Message(
        title="No wire signal",
        text="Make sure the base station is connected to power supply. Disconnect the power supply and reconnect after 10 seconds. Check connection of the perimeter wire to the base station. Check for breaks in the perimeter wire.",
    ),
    48: Message(
        title="Failure",
        text="We are during the BIT edeg near wire test and end of edge is detected",
    ),
    50: Message(title="Recharge battery", text="Mower needs to be recharged (50)"),
    53: Message(title="Recharge battery", text="Mower needs to be recharged (53)"),
    54: Message(title="Recharge battery", text="Mower needs to be recharged (54)"),
    55: Message(title="Recharge battery", text="Mower needs to be recharged (55)"),
    57: Message(
        title="Stuck In place", text="Mower needs your help, please restart (57)"
    ),
    59: Message(
        title="Stuck In place", text="Mower needs your help, please restart (59)"
    ),
    60: Message(
        title="Mowing motor problem", text="Mower needs your help, please restart (60)"
    ),
    67: Message(
        title="Failure", text="Mower needs your help, place mower in base station  (67)"
    ),
    69: Message(
        title="Wait…",
        text="Charging operation was stopped in order to send a robot operation GSM message",
    ),
    72: Message(
        title="Please start the operation elsewhere",
        text="Mower needs your help, please restart (72)",
    ),
    75: Message(
        title="No wire signal",
        text="Make sure the base station is connected to power supply. Disconnect the power supply and reconnect after 10 seconds. Check connection of the perimeter wire to the base station. Check for breaks in the  perimeter wire.",
    ),
    79: Message(
        title="Stuck In place", text="Mower needs your help, please restart (79)"
    ),
    80: Message(
        title="Stuck In place", text="Mower needs your help, please restart (80)"
    ),
    81: Message(
        title="Lift was detected", text="Mower needs your help, please restart (81)"
    ),
    82: Message(
        title="Stuck In place", text="Mower needs your help, please restart (82)"
    ),
    86: Message(
        title="Stuck In place", text="Mower needs your help, please restart (86)"
    ),
    89: Message(
        title="Stuck In place",
        text="Mower needs your help, place mower in base station and check charging (89)",
    ),
    91: Message(
        title="Help needed; restart in new location",
        text="Mower needs your help, please restart (91)",
    ),
    92: Message(
        title="Bumper was pressed", text="Mower needs your help, please restart (92)"
    ),
    93: Message(
        title="Stuck In place", text="Mower needs your help, please restart (93)"
    ),
    94: Message(
        title="Stuck In place",
        text="Mower needs your help, place mower in base station and check charging (94)",
    ),
    95: Message(
        title="Bumper was pressed", text="Mower needs your help, please restart (95)"
    ),
    98: Message(
        title="Help needed; restart in new location",
        text="Mower needs your help, please restart (98)",
    ),
    99: Message(
        title="Stuck In place", text="Mower needs your help, please restart (99)"
    ),
    100: Message(
        title="Operation time completed",
        text="We reached the required mowing time in the current active zone",
    ),
    101: Message(
        title="Stuck In place", text="Multiple robot Slippage events are detected."
    ),
    102: Message(
        title="Base station pairing required",
        text="Mower needs your help, place mower in base station: wait for at least 20 seconds for mower to pair with base station (102)",
    ),
    103: Message(
        title="Help needed; restart in new location",
        text="Mower needs your help, please restart (103)",
    ),
    104: Message(
        title="Help needed; restart in new location",
        text="Mower needs your help, please restart (104)",
    ),
    105: Message(
        title="Help needed; restart in new location",
        text="Mower needs your help, please restart (105)",
    ),
    106: Message(
        title="Disabled mode is active",
        text="please re-insert the disabling key to continue operation (106)",
    ),
    107: Message(title="Bumper was pressed", text="Body Assembly removed"),
    108: Message(title="Battery compartment door is open", text="Battery door is open"),
    113: Message(
        title="Cover is opened",
        text="Operation stopped because cover is open. Please close cover to enable operation (113)",
    ),
    127: Message(
        title="One-time setup needs to be completed",
        text="Your robot must complete the initial setup, to ensure proper functionality",
    ),
    501: Message(title="Failure", text="Please call service (501)"),
    502: Message(title="Failure", text="Please call service (502)"),
    503: Message(
        title="Failure",
        text="Mower needs your help, please restart operation. If problem continues please call service  (503)",
    ),
    504: Message(
        title="Failure",
        text="Mower needs your help, please restart operation. If problem continues please call service  (504)",
    ),
    505: Message(
        title="Failure",
        text="Mower needs your help, please restart operation. If problem continues please call service  (505)",
    ),
    506: Message(title="Failure", text="Please call service (506)"),
    507: Message(
        title="Failure",
        text="Mower needs your help, please restart operation. If problem continues please call service  (507)",
    ),
    508: Message(title="Failure", text="Please call service (508)"),
    509: Message(title="Failure", text="Please call service (509)"),
    513: Message(
        title="Failure",
        text="Mower needs your help, please restart operation. If problem continues please call service  (513)",
    ),
    515: Message(
        title="Failure",
        text="Mower needs your help, please restart operation. If problem continues please call service  (515)",
    ),
    518: Message(
        title="Failure",
        text="Mower needs your help, please restart operation. If problem continues please call service  (518)",
    ),
    520: Message(
        title="Failure",
        text="Mower needs your help, please restart operation. If problem continues please call service  (520)",
    ),
    521: Message(
        title="Failure",
        text="Mower needs your help, please restart operation. If problem continues please call service  (521)",
    ),
    522: Message(title="Failure", text="Please call service (522)"),
    524: Message(title="Failure", text="Please call service (524)"),
    525: Message(title="Failure", text="Please call service (525)"),
    528: Message(
        title="Failure",
        text="Mower needs your help, please restart operation. If problem continues please call service  (528)",
    ),
    530: Message(
        title="Failure",
        text="Mower needs your help, please restart operation. If problem continues please call service  (530)",
    ),
    531: Message(
        title="Failure",
        text="Mower needs your help, please restart operation. If problem continues please call service  (531)",
    ),
    532: Message(
        title="Failure",
        text="Mower needs your help, please restart operation. If problem continues please call service  (532)",
    ),
    533: Message(
        title="Failure",
        text="Mower needs your help, please restart operation. If problem continues please call service  (533)",
    ),
    534: Message(
        title="Failure",
        text="Mower needs your help, please restart operation. If problem continues please call service  (534)",
    ),
    536: Message(
        title="Failure",
        text="Mower needs your help, please restart operation. If problem continues please call service  (534)",
    ),
}

RT_MESSAGES: dict[int, Message] = {
    1: Message(title="Passed", text="Operation Passed."),
    2: Message(
        title="Operation Failed.", text="The Test or Calibration performed has Failed."
    ),
    3: Message(title="Wait", text="Please wait for the process to finish…"),
    4: Message(
        title="No Wire Signal",
        text="Confirm power supply is plugged into the power outlet. Check power supply and perimter wire connection to the Base Station. Check the indication on the Base Station.",
    ),
    5: Message(
        title="Recharge Battery", text="Low battery voltage. Recharge the battery."
    ),
    6: Message(
        title="Wheels in The Air",
        text="Drive wheels have lost their grip with the ground or the mower is lifted.",
    ),
    7: Message(
        title="Key Pressed",
        text="One of the operating panel buttons is constantly pressed.",
    ),
    8: Message(
        title="Low Temperature",
        text="Ambiance temperature is lower than 5ºC (41ºF). The mower will resume automatically.",
    ),
    10: Message(
        title="Check Mowing Height",
        text="Switch Power Off. Mowing motor is loaded. Check grass height and insure nothing is obstructing the blade rotation.",
    ),
    11: Message(
        title="Check Power",
        text="Confirm power supply is plugged into the power outlet. Check power supply connection to the Base Station. Check charging contacts.",
    ),
    12: Message(
        title="Keep Charged",
        text="Keep your mower charged at all times, if it is not being used.",
    ),
    13: Message(
        title="Base Problem",
        text="The mower is failing to enter the Base Station. Adjust position and clean charging contacts.",
    ),
    14: Message(
        title="Start Elsewhere",
        text="Check the ground and the drive wheels. Restart elsewhere. If persists, refer to Troubleshooting section of the User Guide.",
    ),
    15: Message(
        title="Cross Outside",
        text="Some issue was found along the perimeter. Check ground, increase cutting height, or move wire inward.",
    ),
    16: Message(
        title="Incorrect Connection",
        text="Swap (reverse) the perimeter wire connection at the Base Station.",
    ),
    17: Message(
        title="Start Inside", text="Place the mower inside the lawn and start it again."
    ),
    18: Message(
        title="Stuck in Place",
        text="Check ground where stuck and drive wheel rotation is not blocked. Restart elsewhere.",
    ),
    19: Message(title="Starting Point 1 Problem"),
    20: Message(title="Starting Point 2 Problem"),
    21: Message(title="Subzone 3 Entry Problem"),
    22: Message(
        title="Lift Calibration Required",
        text="Press GO button on the mower to start lift sensor calibration process",
    ),
    23: Message(title="Base search is disabled"),
    24: Message(
        title="Short Operation Time",
        text="The actual operation time was shorter than expected.",
    ),
    25: Message(
        title="Waiting for Signal…",
        text="No signal is detected and operation has stopped. Check all power cable connections. The mower will resume automatically once power is restored.",
    ),
    26: Message(
        title="Calibrate Wire Sensor 1", text="Turn wire signal 'Off' then press GO."
    ),
    27: Message(
        title="Calibrate Wire Sensor 2", text="Turn wire signal 'On' then press GO."
    ),
    28: Message(
        title="Check Mowing Motor",
        text="Switch Power Off. Mowing motor is loaded. Check grass height and insure nothing is obstructing the blade rotation.",
    ),
    31: Message(
        title="Learning Edge Distance",
        text="Your mower is learning the distance of the Perimeter Wire in a Separated Zone. Press STOP after completing a full circle around the lawn.",
    ),
    34: Message(
        title="Test Wire Position",
        text="Walk alongside your mower while it is following the edge to test the wire position.",
    ),
    35: Message(
        title="Test Edge Mode",
        text="Place the mower into the Base Station. Press GO to start. The mower will follow Edge back to Base Station.",
    ),
    36: Message(
        title="Test Near Wire Follow",
        text="Place mower near the edge. Press OK to start. The mower will follow Edge at maximum Near Wire Follow distance.",
    ),
    37: Message(title="Demo Mode", text="Mower is in Demo Mode."),
    40: Message(
        title="Place robot in Base Station",
        text="Place the mower into the Base Station before beginning the process of adding a starting point.",
    ),
    41: Message(
        title="Alarm will soon Activate.",
        text="Press OK to deactivate theft protection alarm.",
    ),
    42: Message(
        title="Mow Motor Overheat",
        text="The mowing motor has been overloaded for too long. The mower will resume automatically.",
    ),
    43: Message(
        title="Mow Overheat",
        text="The mowing motor(s) are overheating. Wait for cooldown. Operation will restart automatically.",
    ),
    44: Message(title="Warning! Motors will now be activated."),
    45: Message(
        title="Calibrate Lift Sensor 1",
        text="Place the mower on the ground then press GO",
    ),
    46: Message(title="Calibrate Lift Sensor 2", text="Lift mower then press GO."),
    47: Message(
        title="Mower is Lifted",
        text="For safety purposes, switch the power off before lifting the mower.",
    ),
    48: Message(
        title="Theft protection is active",
        text="It's impossible to switch the mower off as long as the theft protection is active.",
    ),
    50: Message(
        title="Disabling Device Removed",
        text="Insert the Disabling Device to operate the mower",
    ),
    51: Message(
        title="Standby Mode",
        text="Your mower is currently charging in standby mode. Switch ON for operation.",
    ),
    52: Message(
        title="Adjust the Wire",
        text="The mower has bumped into something along the edge and backed up. Move the wire slightly inward. Press OK to continue.",
    ),
    60: Message(
        title="Intensity Error",
        text="The Intensity set is too high for your lawn area.",
    ),
    61: Message(
        title="Decrease Inactive Time",
        text="Too many Inactive days/hours have been set for your lawn area or Mowing Frequency (Interval) is too high.",
    ),
    62: Message(
        title="Alarm will soon Activate.",
        text="Press OK to deactivate theft protection alarm.",
    ),
    63: Message(
        title="Inactive Hours 2 modified via App",
        text='Inactive hours cannot be set via the mower as long as "Inactive Hours 2" are enabled via the app.',
    ),
    64: Message(
        title="No Base Station Found",
        text='"Searching Base Station" operation cannot be performed in a zone without a Base Station.',
    ),
    85: Message(
        title="Invalid system configuration",
        text="The installed Software and Hardware configurations are not compatible.",
    ),
    86: Message(
        title="Waiting for Signal…",
        text="No signal is detected and operation has stopped. Check all power cable connections. The mower will resume automatically once power is restored.",
    ),
    87: Message(
        title="Mow Motor Overheat",
        text="The mowing motor has been overloaded for too long. The mower will resume automatically.",
    ),
    88: Message(
        title="Drive Motor Overheat",
        text="The drive motor(s) has been overloaded for too long. The mower will resume automatically.",
    ),
    89: Message(
        title="Child Lock is activated",
        text="To operate your mower, please press GO + STOP together, then select the desired command.",
    ),
    90: Message(title="Starting Point 1 Problem"),
    91: Message(title="Starting Point 2 Problem"),
    92: Message(title="Subzone 3 Entry Problem"),
    93: Message(title="Subzone 4 Entry Problem"),
    94: Message(
        title="Disabling Device Removed",
        text="Insert the Disabling Device to operate the mower",
    ),
    95: Message(title="Rain Sensing…"),
    501: Message(title="Wire signal off reading is higher than wire signal on reading"),
    502: Message(
        title="Wire reading indicates calibration failed because either the signal off amplitude readings or the signal on amplitude readings exceed their tolerance"
    ),
    503: Message(
        title="Wire reading indicates calibration failed because we detect that robot is not inside the garden during the calibration with signal on"
    ),
    504: Message(
        title="Wire reading indicates calibration failed because we detect that in/out readings are invalid"
    ),
    505: Message(
        title="Wire reading indicates calibration failed because the difference between wire max signal threshold and wire amplitude set point is too big"
    ),
    506: Message(
        title="Wire reading indicates calibration failed because the wire no signal gain is too small"
    ),
    507: Message(
        title="Drive Motor Disconnected",
        text="Open mower's cover and check drive motors' connections",
    ),
    508: Message(title="Drive configuration is invalid"),
    509: Message(title="Tilt calibration failed"),
    510: Message(
        title="Tilt calibration failed because accelerometer readings are not in tolerance"
    ),
    511: Message(title="Accelerometer failure"),
    512: Message(title="Battery voltage calibration failure"),
    513: Message(title="Error 513"),
    514: Message(title="Error 514"),
    515: Message(title="Error 515"),
    516: Message(title="Error 516"),
    517: Message(title="Error 517"),
    518: Message(title="Error 518"),
    519: Message(title="Error 519"),
    520: Message(title="Error 520"),
    521: Message(
        title="Disabling Device Removed",
        text="Insert the Disabling Device to operate the mower",
    ),
    522: Message(
        title="Lift Calibration Required",
        text="Press GO button on the mower to start lift sensor calibration process",
    ),
    525: Message(
        title="Lift Calibration Required",
        text="Press GO button on the mower to start lift sensor calibration process",
    ),
    527: Message(
        title="Mowing Motor Disconnected",
        text="Open mower's cover and check mowing motor's connection",
    ),
}
