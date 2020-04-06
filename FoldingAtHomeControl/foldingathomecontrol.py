"""Get Information on your Folding@Home Clients."""
import asyncio
import logging
from uuid import uuid4
from typing import Optional, Callable
from .const import COMMANDS, PyOnMessageTypes
from .exceptions import (
    FoldingAtHomeControlAuthenticationRequired,
    FoldingAtHomeControlConnectionFailed,
)
from .pyonparser import convert_pyon_to_json

from .serialconnection import SerialConnection

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
        self,
        address: str,
        port: int = 36330,
        password: Optional[str] = None,
        reconnect_enabled: bool = True,
    ) -> None:
        """Initialize connection data."""
        self._serialconnection = SerialConnection(address, port, password)
        self._reconnect_enabled: bool = reconnect_enabled

        self._callbacks: dict = {}
        self._connect_task: Optional[asyncio.Task] = None
        self._on_disconnect: Optional[Callable] = None

    async def try_connect_async(self, timeout: int) -> None:
        """Try to connect with timeout."""
        try:
            self._connect_task = asyncio.get_event_loop().create_task(
                self._serialconnection.connect_async()
            )
            _, pending = await asyncio.wait([self._connect_task], timeout=timeout)
            if self._connect_task in pending:
                try:
                    self._connect_task.cancel()
                    await self._connect_task
                except asyncio.CancelledError:
                    pass
                raise FoldingAtHomeControlConnectionFailed
        except asyncio.streams.IncompleteReadError:
            raise FoldingAtHomeControlConnectionFailed

    async def connect_async(self) -> None:
        """Try until connect succeeds."""
        while not self.is_connected:
            try:
                await self.try_connect_async(CONNECT_TIMEOUT)
            except ConnectionRefusedError:
                _LOGGER.error(
                    "Could not connect to %s:%d",
                    self._serialconnection.address,
                    self._serialconnection.port,
                )
                await asyncio.sleep(SLEEP_IN_SECONDS)
            except FoldingAtHomeControlConnectionFailed:
                _LOGGER.error(
                    "Timeout while trying to connect to %s:%d",
                    self._serialconnection.address,
                    self._serialconnection.port,
                )
            except asyncio.CancelledError as cancelled_error:
                await self._cleanup_async(None, cancelled_error)

    def register_callback(self, callback: Callable) -> Callable:
        """Register a callback for received data."""
        uuid = uuid4()
        self._callbacks[uuid] = callback
        _LOGGER.debug("Registered callback")

        def remove_callback() -> None:
            """Remove callback."""
            del self._callbacks[uuid]

        return remove_callback

    async def start(self) -> None:
        """Start listening to the socket."""
        task = None
        while self.is_connected:
            try:
                await self._try_parse_pyon_message_async()
            except asyncio.streams.IncompleteReadError:
                await self._call_on_disconnect_async()
            except asyncio.CancelledError as cancelled_error:
                await self._cleanup_async(task, cancelled_error)

    async def subscribe_async(
        self, commands: list = list(COMMANDS.values())
    ):  # pylint: disable=dangerous-default-value
        """Start a subscription to commands."""
        command_package = "".join(commands)
        await self._serialconnection.send_async(command_package)

    async def request_work_server_assignment_async(self) -> None:
        """Request work server assignment from the assignmentserver."""
        await self._serialconnection.send_async("request-ws\n")

    def on_disconnect(self, func: Callable) -> None:
        """Register a method to be executed when the connection is disconnected."""
        self._on_disconnect = func

    async def _try_parse_pyon_message_async(self) -> None:
        """Read from the socket until a full message has been received."""
        raw_message = await self._serialconnection.read_async()
        if PY_ON_MESSAGE_HEADER in raw_message:
            raw_messages = []
            message_type = get_message_type_from_message(raw_message)
            while PY_ON_MESSAGE_FOOTER not in raw_message:
                raw_message = await self._serialconnection.read_async()
                raw_messages.append(raw_message)
            raw_messages.pop()  # Remove PY_ON_MESSAGE_FOOTER
            message = "".join(raw_messages)
            json_object = convert_pyon_to_json(message)
            await self._call_callbacks_async(message_type, json_object)
        elif PY_ON_ERROR in raw_message:
            error_message = raw_message.strip()
            _LOGGER.error("Received error: %s", error_message)
            if (
                UNAUTHENTICATED_INDICATOR in raw_message
                and not self._serialconnection.is_authenticated
            ):
                _LOGGER.error("This could mean a password is needed.")
                raise FoldingAtHomeControlAuthenticationRequired(
                    "Seems like a password is required but was not provided."
                )
            await self._call_callbacks_async(
                PyOnMessageTypes.ERROR.value, error_message
            )

    async def _call_callbacks_async(self, message_type: str, message: str) -> None:
        """Pass the message to all callbacks."""
        for callback in self._callbacks.values():
            if asyncio.iscoroutinefunction(callback):
                await callback(message_type, message)
            else:
                callback(message_type, message)

    async def _call_on_disconnect_async(self) -> None:
        """Call and if needed await on_disconnect callback."""
        if self._on_disconnect is not None:
            if asyncio.iscoroutinefunction(self._on_disconnect):
                await self._on_disconnect()
            else:
                self._on_disconnect()
        elif self._reconnect_enabled:
            await self.connect_async()
            await self.subscribe_async()

    async def _cleanup_async(
        self, task: Optional[asyncio.Task], cancelled_error: Exception
    ) -> None:
        """Clean up running tasks and writers."""
        if task is not None:
            task.cancel()
            await task
        if self._connect_task is not None:
            self._connect_task.cancel()
            await self._connect_task
        if self._serialconnection is not None:
            await self._serialconnection.cleanup_async()
        _LOGGER.info("Got Cancelled")
        raise cancelled_error

    @property
    def is_connected(self) -> bool:
        """Is the client connected."""
        return self._serialconnection.is_connected


def get_message_type_from_message(message: str) -> str:
    """Parses the message_type from the message."""
    return message.split(" ")[2].replace("\n", "")
