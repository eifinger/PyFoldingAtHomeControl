"""Get Information on your Folding@Home Clients."""
import asyncio
import logging
from .const import COMMANDS
from .pyonparser import convert_pyon_to_json

_LOGGER = logging.getLogger(__name__)

PY_ON_MESSAGE_HEADER = "PyON 1"
PY_ON_MESSAGE_FOOTER = "---"


class FoldingAtHomeController:
    """Connect to Folding@Home Client."""

    def __init__(self, address: str, port: int = 36330, password: str = None) -> None:
        """Initialize connection data."""
        self._address: str = address
        self._port: int = port
        self._password: str = password

        self._reader = None
        self._writer = None
        self._callbacks_by_message_type: dict = {}
        self._is_connected: bool = False

    async def _connect_and_subscribe(self) -> None:
        """Open the connection to the socket."""
        self._reader, self._writer = await asyncio.open_connection(
            self._address, self._port
        )
        self._is_connected = True
        welcome_message = await self._read_async()
        _LOGGER.debug("Received welcome message: %s", welcome_message)
        if self._password is not None:
            self._authenticate()
        await self._subscribe_async()

    async def _authenticate(self) -> None:
        """Use the provided password to authenticate."""
        auth_string = f"auth {self._password}\n"
        await self._send_async(auth_string)
        auth_response = await self._read_async()
        _LOGGER.debug("Authentication response: %s", auth_response)

    def register_callback_for_message_type(self, message_type, callback) -> None:
        """Register a callback for received data."""
        if message_type not in self._callbacks_by_message_type:
            self._callbacks_by_message_type[message_type] = []
        self._callbacks_by_message_type[message_type].append(callback)
        _LOGGER.debug("Registered callback for message_type: %s", message_type)

    async def run(self) -> None:
        """Keep the server running."""
        while True:
            try:
                if not self._is_connected:
                    await self._connect_and_subscribe()
                await self._try_parse_pyon_message()
            except asyncio.CancelledError as cancelled_error:
                await self._writer.drain()
                self._writer.close()
                _LOGGER.info("Cancelled")
                raise cancelled_error

    async def _read_async(self) -> str:
        """Read string from the socket and return it."""
        data = await self._reader.readuntil()
        return data.decode()

    async def _try_parse_pyon_message(self) -> str:
        """Read from the socket until a full message has been received."""
        raw_message = await self._read_async()
        if PY_ON_MESSAGE_HEADER in raw_message:
            raw_messages = []
            message_type = self._get_message_type_from_message(raw_message)
            while PY_ON_MESSAGE_FOOTER not in raw_message:
                raw_message = await self._read_async()
                raw_messages.append(raw_message)
            raw_messages.pop()  # Remove PY_ON_MESSAGE_FOOTER
            message = "".join(raw_messages)
            json_object = convert_pyon_to_json(message)
            await self._call_callbacks_async(message_type, json_object)

    def _get_message_type_from_message(self, message):
        """Parses the message_type from the message."""
        return message.split(" ")[2].replace("\n", "")

    async def _call_callbacks_async(self, message_type, message: str) -> None:
        """Pass the message to all callbacks."""
        if message_type in self._callbacks_by_message_type:
            for callback in self._callbacks_by_message_type[message_type]:
                callback(message)
        else:
            _LOGGER.error("Unknown PyON type: %s", message_type)

    async def _send_async(self, message: str) -> None:
        """Send data."""
        self._writer.write(message.encode())
        await self._writer.drain()

    async def _subscribe_async(self):
        """Send commands to subscribe to infos."""
        command_package = "".join(COMMANDS.values())
        await self._send_async(command_package)
