"""Serial Connection for FoldingAtHomeControl."""
import asyncio
import logging
from asyncio import Future, Lock, StreamReader, StreamWriter
from typing import Any, Optional

from .exceptions import (
    FoldingAtHomeControlAuthenticationFailed,
    FoldingAtHomeControlConnectionFailed,
)

_LOGGER = logging.getLogger(__name__)

MAX_AUTHENTICATION_MESSAGE_COUNT = 5


class SerialConnection:
    """Serial Connection for FoldingAtHomeControl."""

    def __init__(
        self,
        address: str,
        port: int = 36330,
        password: Optional[str] = None,
        read_timeout: int = 5,
    ) -> None:
        """Initialize connection data."""
        self._address: str = address
        self._port: int = port
        self._password: Optional[str] = password
        self._read_timeout: int = read_timeout

        self._reader: StreamReader
        self._writer: StreamWriter
        self._callbacks: dict = {}
        self._is_connected: bool = False
        self._is_authenticated: bool = False
        self._reader_lock: Lock = Lock()
        self._writer_lock: Lock = Lock()
        self._read_future: Optional[Future] = None

    async def connect_async(self) -> None:
        """Open the connection to the socket."""
        self._reader, self._writer = await asyncio.open_connection(
            self._address, self._port
        )
        await self._receive_welcome_message_async()
        if self._password is not None:
            await self._authenticate_async()
        self._is_connected = True

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
        _LOGGER.debug(
            "Did not receive a valid authentication response in the last %d messages.",
            MAX_AUTHENTICATION_MESSAGE_COUNT,
        )
        raise FoldingAtHomeControlAuthenticationFailed(
            "Did not receive a valid authentication response."
        )

    def set_read_timeout(self, timeout: int) -> None:
        """Set the read timeout in seconds."""
        self._read_timeout = timeout

    async def read_async(self) -> Any:
        """Read string from the socket and return it."""
        async with self._reader_lock:
            try:
                self._read_future = asyncio.ensure_future(self._reader.readuntil())
                completed, pending = await asyncio.wait(
                    [self._read_future], timeout=self._read_timeout
                )
                if self._read_future in pending:
                    try:
                        self._read_future.cancel()
                        await self._read_future
                    except asyncio.CancelledError:
                        pass
                    _LOGGER.debug(
                        "Timeout while trying to read from %s:%d",
                        self.address,
                        self.port,
                    )
                    self._is_connected = False
                    raise FoldingAtHomeControlConnectionFailed
                future_results = await asyncio.gather(*completed)
                await asyncio.gather(*pending)
            except asyncio.streams.IncompleteReadError as error:
                self._is_connected = False
                raise error
            return future_results[0].decode()

    async def send_async(self, message: str) -> None:
        """Send data."""
        async with self._writer_lock:
            self._writer.write(message.encode())
            await self._writer.drain()

    async def cleanup_async(self) -> None:
        """Clean up running tasks and writers."""
        if self._read_future is not None:
            self._read_future.cancel()
            await self._read_future
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

    @property
    def read_timeout(self) -> int:
        """The configured read timeout."""
        return self._read_timeout
