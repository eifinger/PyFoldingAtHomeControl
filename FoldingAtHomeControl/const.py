"""Constants for FoldingAtHomeControl."""

from enum import Enum

COMMAND_OPTIONS = "options"
COMMAND_QUEUE_INFO = "queue-info"
COMMAND_SLOT_INFO = "slot-info"
COMMAND_REQUEST_WORKSERVER_ASSIGNMENT = "request-ws"
COMMAND_PAUSE = "pause"
COMMAND_UNPAUSE = "unpause"
COMMAND_SHUTDOWN = "shutdown"

SUBSCRIBE_COMMANDS = [COMMAND_OPTIONS, COMMAND_QUEUE_INFO, COMMAND_SLOT_INFO]
UNSUBSCRIBE_ALL_COMMAND = "updates clear"

PY_ON_MESSAGE_HEADER = "PyON 1"
PY_ON_MESSAGE_FOOTER = "---"
PY_ON_ERROR = "ERROR"
UNAUTHENTICATED_INDICATOR = "unknown command or variable 'updates'"


class PyOnMessageTypes(Enum):
    """Supported Message Types."""

    UNITS = "units"
    OPTIONS = "options"
    SLOTS = "slots"
    ERROR = "error"
