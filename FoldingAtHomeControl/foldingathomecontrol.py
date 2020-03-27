"""Get Information on your Folding@Home Clients."""
import asyncio
from asyncio import StreamReader, StreamWriter
import logging
from typing import Optional, Callable, Coroutine
from .const import COMMANDS
from .exceptions import (
    FoldingAtHomeControlAuthenticationFailed,
    FoldingAtHomeControlAuthenticationRequired,
)
from .pyonparser import convert_pyon_to_json

_LOGGER = logging.getLogger(__name__)

PY_ON_MESSAGE_HEADER = "PyON 1"
PY_ON_MESSAGE_FOOTER = "---"
PY_ON_ERROR = "ERROR"
SLEEP_IN_SECONDS = 10
MAX_AUTHENTICATION_MESSAGE_COUNT = 5
UNAUTHENTICATED_INDICATOR = "unknown command or variable 'updates'"
CONNECT_TIMEOUT = 5


class FoldingAtHomeController:
    """Connect to Folding@Home Client."""

    def __init__(
        self, address: str, port: int = 36330, password: Optional[str] = None
    ) -> None:
        """Initialize connection data."""
        self._address: str = address
        self._port: int = port
        self._password: Optional[str] = password

        self._reader: StreamReader
        self._writer: StreamWriter
        self._callbacks: list = []
        self._is_connected: bool = False
        self._is_authenticated: bool = False

    def register_callback(self, callback: Callable) -> None:
        """Register a callback for received data."""
        self._callbacks.append(callback)
        _LOGGER.debug("Registered callback")

    async def run(self) -> None:
        """Keep the server running."""
        task = None
        while True:
            try:
                if self._is_connected:
                    await self._try_parse_pyon_message_async()
                else:
                    try:
                        await self._try_connect_async(CONNECT_TIMEOUT)
                    except ConnectionRefusedError:
                        _LOGGER.error(
                            "Could not connect to %s:%d", self._address, self._port
                        )
                        asyncio.sleep(SLEEP_IN_SECONDS)
            except asyncio.CancelledError as cancelled_error:
                self._cleanup(task, cancelled_error)

    async def _try_connect_async(self, timeout: int) -> None:
        """Try to connect with timeout."""
        task = asyncio.get_event_loop().create_task(self._connect_and_subscribe())
        _, pending = await asyncio.wait({task}, timeout=5)
        if task in pending:
            _LOGGER.error(
                "Timeout while trying to connect to %s:%d", self._address, self._port,
            )
            task.cancel()
            await task

    async def _connect_and_subscribe(self) -> None:
        """Open the connection to the socket."""
        self._reader, self._writer = await asyncio.open_connection(
            self._address, self._port
        )
        self._is_connected = True
        await self._receive_welcome_message_async()
        if self._password is not None:
            await self._authenticate_async()
        await self._subscribe_async()

    async def _receive_welcome_message_async(self) -> None:
        """Convenience method to receive strip and log the welcome message."""
        welcome_message = await self._read_async()
        # Strip clearscreen: \x1b[H\x1b[2J
        welcome_message = welcome_message[7:]
        # Strip linebreaks
        welcome_message = welcome_message.strip()
        _LOGGER.debug("Received welcome message: %s", welcome_message)

    async def _authenticate_async(self) -> None:
        """Use the provided password to authenticate."""
        auth_string = f"auth {self._password}\n"
        await self._send_async(auth_string)
        await self._wait_for_auth_response_async()

    async def _wait_for_auth_response_async(self) -> None:
        """Wait until a valid auth response is received."""
        auth_response = ""
        for _ in range(MAX_AUTHENTICATION_MESSAGE_COUNT):
            if "OK" in auth_response:
                self._is_authenticated = True
                _LOGGER.debug("Authentication response: %s", auth_response)
                return
            if "FAILED" in auth_response:
                _LOGGER.debug("Authentication response: %s", auth_response)
                raise FoldingAtHomeControlAuthenticationFailed("Password is incorrect.")
            auth_response = await self._read_async()
        _LOGGER.error(
            "Did not receive a valid authentication response in the last %d messages.",
            MAX_AUTHENTICATION_MESSAGE_COUNT,
        )
        raise FoldingAtHomeControlAuthenticationFailed(
            "Did not receive a valid authentication response."
        )

    async def _read_async(self) -> str:
        """Read string from the socket and return it."""
        data = await self._reader.readuntil()
        return data.decode()

    async def _try_parse_pyon_message_async(self) -> None:
        """Read from the socket until a full message has been received."""
        raw_message = await self._read_async()
        if PY_ON_MESSAGE_HEADER in raw_message:
            raw_messages = []
            message_type = get_message_type_from_message(raw_message)
            while PY_ON_MESSAGE_FOOTER not in raw_message:
                raw_message = await self._read_async()
                raw_messages.append(raw_message)
            raw_messages.pop()  # Remove PY_ON_MESSAGE_FOOTER
            message = "".join(raw_messages)
            json_object = convert_pyon_to_json(message)
            await self._call_callbacks_async(message_type, json_object)
        elif PY_ON_ERROR in raw_message:
            _LOGGER.error("Received error: %s", raw_message.strip())
            if UNAUTHENTICATED_INDICATOR in raw_message and not self._is_authenticated:
                _LOGGER.error("This could mean a password is needed.")
                raise FoldingAtHomeControlAuthenticationRequired(
                    "Seems like a password is required but was not provided."
                )

    async def _call_callbacks_async(self, message_type: str, message: str) -> None:
        """Pass the message to all callbacks."""
        for callback in self._callbacks:
            callback(message_type, message)

    async def _send_async(self, message: str) -> None:
        """Send data."""
        self._writer.write(message.encode())
        await self._writer.drain()

    async def _subscribe_async(self) -> None:
        """Send commands to subscribe to infos."""
        command_package = "".join(COMMANDS.values())
        await self._send_async(command_package)

    async def _cleanup(
        self, task: Optional[Coroutine], cancelled_error: Exception
    ) -> None:
        """Clean up running tasks and writers."""
        if task is not None:
            task.cancel()
            await task
        if hasattr(self, "_writer"):
            await self._writer.drain()
            self._writer.close()
        _LOGGER.info("Got Cancelled")
        raise cancelled_error


def get_message_type_from_message(message: str) -> str:
    """Parses the message_type from the message."""
    return message.split(" ")[2].replace("\n", "")
