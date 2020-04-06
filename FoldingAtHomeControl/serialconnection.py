"""Serial Connection for FoldingAtHomeControl."""
import asyncio
from asyncio import StreamReader, StreamWriter, Lock
import logging
from typing import Optional
from .exceptions import (
    FoldingAtHomeControlAuthenticationFailed,
    FoldingAtHomeControlNotConnected,
)

_LOGGER = logging.getLogger(__name__)

MAX_AUTHENTICATION_MESSAGE_COUNT = 5


class SerialConnection:
    """Serial Connection for FoldingAtHomeControl."""

    def __init__(
        self, address: str, port: int = 36330, password: Optional[str] = None
    ) -> None:
        """Initialize connection data."""
        self._address: str = address
        self._port: int = port
        self._password: Optional[str] = password

        self._reader: StreamReader
        self._writer: StreamWriter
        self._callbacks: dict = {}
        self._is_connected: bool = False
        self._is_authenticated: bool = False
        self._reader_lock: Lock = Lock()
        self._writer_lock: Lock = Lock()

    async def connect_async(self) -> None:
        """Open the connection to the socket."""
        self._reader, self._writer = await asyncio.open_connection(
            self._address, self._port
        )
        self._is_connected = True
        await self._receive_welcome_message_async()
        if self._password is not None:
            await self._authenticate_async()

    async def _receive_welcome_message_async(self) -> None:
        """Convenience method to receive strip and log the welcome message."""
        welcome_message = await self.read_async()
        # Strip clearscreen: \x1b[H\x1b[2J
        welcome_message = welcome_message[7:]
        # Strip linebreaks
        welcome_message = welcome_message.strip()
        _LOGGER.debug("Received welcome message: %s", welcome_message)

    async def _authenticate_async(self) -> None:
        """Use the provided password to authenticate."""
        auth_string = f"auth {self._password}\n"
        await self.send_async(auth_string)
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
            auth_response = await self.read_async()
        _LOGGER.error(
            "Did not receive a valid authentication response in the last %d messages.",
            MAX_AUTHENTICATION_MESSAGE_COUNT,
        )
        raise FoldingAtHomeControlAuthenticationFailed(
            "Did not receive a valid authentication response."
        )

    async def read_async(self) -> str:
        """Read string from the socket and return it."""
        async with self._reader_lock:
            if not self._is_connected:
                raise FoldingAtHomeControlNotConnected
            try:
                data = await self._reader.readuntil()
            except asyncio.streams.IncompleteReadError as error:
                self._is_connected = False
                raise error
            return data.decode()

    async def send_async(self, message: str) -> None:
        """Send data."""
        async with self._writer_lock:
            if not self._is_connected:
                raise FoldingAtHomeControlNotConnected
            self._writer.write(message.encode())
            await self._writer.drain()

    async def cleanup_async(self) -> None:
        """Clean up running tasks and writers."""
        if hasattr(self, "_writer"):
            await self._writer.drain()
            self._writer.close()
        _LOGGER.info("Got Cancelled")

    @property
    def address(self) -> str:
        """The address this is connected to."""
        return self._address

    @property
    def port(self) -> int:
        """The port this is connected to."""
        return self._port

    @property
    def is_connected(self) -> bool:
        """Is it connected?"""
        return self._is_connected

    @property
    def is_authenticated(self) -> bool:
        """Is the connection authenticated?"""
        return self._is_authenticated
