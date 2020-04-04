"""Constants for FoldingAtHomeControl."""

from enum import Enum

COMMANDS = {
    "options": "updates add 0 1 $options\n",
    "queue_info": "updates add 1 1 $queue-info\n",
    "slot_info": "updates add 2 1 $slot-info\n",
}


class PyOnMessageTypes(Enum):
    """Supported Message Types."""

    UNITS = "units"
    OPTIONS = "options"
    SLOTS = "slots"
    ERROR = "error"
