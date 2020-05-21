"""Get Information on your Folding@Home Clients."""
import asyncio
import logging
from typing import Callable, Optional
from uuid import uuid4

from .const import (
    COMMAND_PAUSE,
    COMMAND_REQUEST_WORKSERVER_ASSIGNMENT,
    COMMAND_SHUTDOWN,
    COMMAND_UNPAUSE,
    PY_ON_ERROR,
    PY_ON_MESSAGE_FOOTER,
    PY_ON_MESSAGE_HEADER,
    SUBSCRIBE_COMMANDS,
    UNAUTHENTICATED_INDICATOR,
    UNSUBSCRIBE_ALL_COMMAND,
    PyOnMessageTypes,
)
from .exceptions import (
    FoldingAtHomeControlAuthenticationRequired,
    FoldingAtHomeControlConnectionFailed,
    FoldingAtHomeControlNotConnected,
)
from .pyonparser import convert_pyon_to_json
from .serialconnection import SerialConnection

_LOGGER = logging.getLogger(__name__)

RETRY_WAIT_IN_SECONDS = 10
MAX_AUTHENTICATION_MESSAGE_COUNT = 5
CONNECT_TIMEOUT_IN_SECONDS = 5


class FoldingAtHomeController:
    """Connect to Folding@Home Client."""

    def __init__(
        self,
        address: str,
        port: int = 36330,
        password: Optional[str] = None,
        reconnect_enabled: bool = True,
        read_timeout: int = 15,
        update_rate: int = 5,
    ) -> None:
        """Initialize connection data."""
        self._serialconnection = SerialConnection(address, port, password, read_timeout)
        self._reconnect_enabled: bool = reconnect_enabled

        self._callbacks: dict = {}
        self._connect_task: Optional[asyncio.Future] = None
        self._on_disconnect: Optional[Callable] = None
        self._subscription_counter: int = 0
        self._update_rate = update_rate

    async def try_connect_async(self, timeout: int) -> None:
        """Try to connect with timeout."""
        try:
            self._connect_task = asyncio.ensure_future(
                self._serialconnection.connect_async()
            )
            completed, pending = await asyncio.wait(
                [self._connect_task], timeout=timeout
            )
            if self._connect_task in pending:
                try:
                    self._connect_task.cancel()
                    await self._connect_task
                except asyncio.CancelledError:
                    pass
                _LOGGER.debug(
                    "Timeout while trying to connect to %s:%d",
                    self._serialconnection.address,
                    self._serialconnection.port,
                )
                raise FoldingAtHomeControlConnectionFailed
            try:
                await asyncio.gather(*completed)
                await asyncio.gather(*pending)
            except OSError:
                _LOGGER.debug(
                    "Could not connect to %s:%d",
                    self._serialconnection.address,
                    self._serialconnection.port,
                )
                raise FoldingAtHomeControlConnectionFailed
        except asyncio.streams.IncompleteReadError:
            raise FoldingAtHomeControlConnectionFailed

    async def connect_async(self) -> None:
        """Try until connect succeeds."""
        while not self.is_connected:
            try:
                await self.try_connect_async(CONNECT_TIMEOUT_IN_SECONDS)
            except FoldingAtHomeControlConnectionFailed:
                await asyncio.sleep(RETRY_WAIT_IN_SECONDS)
            except asyncio.CancelledError as cancelled_error:
                await self.cleanup_async(cancelled_error)

    def on_disconnect(self, func: Callable) -> None:
        """Register a method to be executed when the connection is disconnected."""
        self._on_disconnect = func

    def register_callback(self, callback: Callable) -> Callable:
        """Register a callback for received data."""
        uuid = uuid4()
        self._callbacks[uuid] = callback
        _LOGGER.debug("Registered callback")

        def remove_callback() -> None:
            """Remove callback."""
            del self._callbacks[uuid]

        return remove_callback

    def set_read_timeout(self, timeout: int) -> None:
        """Set the read timeout in seconds."""
        self._serialconnection.set_read_timeout(timeout)

    async def set_subscription_update_rate_async(self, update_rate: int) -> None:
        """Set the subscription update rate in seconds."""
        self._update_rate = update_rate
        if self._subscription_counter > 0:
            await self.unsubscribe_all_async()
            await self.subscribe_async()

    async def subscribe_async(  # pylint: disable=dangerous-default-value
        self, commands: list = SUBSCRIBE_COMMANDS
    ) -> None:
        """Start a subscription to commands."""
        subscriptions = []
        for command in commands:
            subscription = f"updates add {self._get_next_subscription_id()} {self._update_rate} ${command}"  # pylint: disable=line-too-long
            subscriptions.append(subscription)

        await self._send_commands_async(subscriptions)

    async def unsubscribe_all_async(self) -> None:
        """Unsubscribe all subscriptions."""
        await self._send_command_async(UNSUBSCRIBE_ALL_COMMAND)

    async def start(self, connect: bool = True, subscribe: bool = True) -> None:
        """Start listening to the socket."""
        if connect:
            await self.connect_async()
        if subscribe:
            await self.subscribe_async()
        while self.is_connected:
            try:
                await self._try_parse_pyon_message_async()
            except (
                asyncio.streams.IncompleteReadError,
                FoldingAtHomeControlConnectionFailed,
            ):
                await self._call_on_disconnect_async()
            except asyncio.CancelledError as cancelled_error:
                _LOGGER.debug("Got cancelled.")
                await self.cleanup_async(cancelled_error)
        _LOGGER.debug("Start ended.")

    async def request_work_server_assignment_async(self) -> None:
        """Request work server assignment from the assignmentserver."""
        await self._send_command_async(COMMAND_REQUEST_WORKSERVER_ASSIGNMENT)

    async def pause_slot_async(self, slot_id: str) -> None:
        """Pause a slot."""
        await self._send_command_async(f"{COMMAND_PAUSE} {slot_id}")

    async def pause_all_slots_async(self) -> None:
        """Pause all slots."""
        await self._send_command_async(COMMAND_PAUSE)

    async def unpause_slot_async(self, slot_id: str) -> None:
        """Unpause a slot."""
        await self._send_command_async(f"{COMMAND_UNPAUSE} {slot_id}")

    async def unpause_all_slots_async(self) -> None:
        """Unpause all slots."""
        await self._send_command_async(COMMAND_UNPAUSE)

    async def shutdown(self) -> None:
        """Shutdown the client."""
        await self._send_command_async(COMMAND_SHUTDOWN)

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
            _LOGGER.debug("Received error: %s", error_message)
            if (
                UNAUTHENTICATED_INDICATOR in raw_message
                and not self._serialconnection.is_authenticated
            ):
                _LOGGER.debug("This could mean a password is needed.")
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
        self._reset_subscription_counter()
        if self._on_disconnect is not None:
            if asyncio.iscoroutinefunction(self._on_disconnect):
                await self._on_disconnect()
            else:
                self._on_disconnect()
        if self._reconnect_enabled:
            await self.connect_async()
            await self.subscribe_async()

    def _get_next_subscription_id(self) -> int:
        """Returns the next id for a subscription"""
        self._subscription_counter += 1
        return self._subscription_counter - 1

    def _reset_subscription_counter(self) -> None:
        """Reset the subscription counter to 0."""
        self._subscription_counter = 0

    async def cleanup_async(self, cancelled_error: Optional[Exception] = None) -> None:
        """Clean up running tasks and writers."""
        if self._connect_task is not None:
            self._connect_task.cancel()
            await self._connect_task
        if self._serialconnection is not None:
            await self._serialconnection.cleanup_async()
        _LOGGER.debug("Cleanup finished")
        if cancelled_error is not None:
            raise cancelled_error

    async def _send_command_async(self, command: str) -> None:
        """Send a command."""
        if not self.is_connected:
            raise FoldingAtHomeControlNotConnected
        await self._serialconnection.send_async(f"{command}\n")

    async def _send_commands_async(self, commands: list) -> None:
        """Send a list of command."""
        if not self.is_connected:
            raise FoldingAtHomeControlNotConnected
        command_package = "\n".join(commands) + "\n"
        await self._serialconnection.send_async(command_package)

    @property
    def is_connected(self) -> bool:
        """Is the client connected."""
        return self._serialconnection.is_connected

    @property
    def read_timeout(self) -> int:
        """The configured read timeout in seconds."""
        return self._serialconnection.read_timeout

    @property
    def update_rate(self) -> int:
        """The subscription update rate in seconds."""
        return self._update_rate


def get_message_type_from_message(message: str) -> str:
    """Parses the message_type from the message."""
    return message.split(" ")[2].replace("\n", "")
