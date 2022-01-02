"""Fixtures for tests."""
import asyncio
from asyncio.streams import StreamReader

import pytest

try:
    from unittest.mock import AsyncMock as MagicMock
except ImportError:
    from unittest.mock import MagicMock

    async def async_magic() -> None:
        """AsyncMock for python <3.8.2"""
        pass

    MagicMock.__await__ = lambda _: async_magic().__await__()
from FoldingAtHomeControl import FoldingAtHomeController
from FoldingAtHomeControl.serialconnection import SerialConnection


@pytest.fixture
def foldingathomecontroller():
    """Create a localhost FoldingAtHomeController."""
    controller = FoldingAtHomeController("localhost")
    return controller


@pytest.fixture
def auth_foldingathomecontroller():
    """Create a localhost FoldingAtHomeController with a password."""
    controller = FoldingAtHomeController("localhost", password="test")
    return controller


@pytest.fixture
def disconnecting_foldingathomecontroller():
    """Create a localhost FoldingAtHomeController."""
    controller = FoldingAtHomeController("localhost", reconnect_enabled=False)
    return controller


@pytest.fixture(name="connection_prepared_stream_reader")
def fixture_connection_prepared_stream_reader():
    """Create a StreamReader and fill it with connection messages."""
    reader = StreamReader()
    reader.feed_data(
        b"\x1b[H\x1b[2JWelcome to the Folding@home Client command server.\n"
    )
    return reader


@pytest.fixture(name="error_prepared_stream_reader")
def fixture_error_prepared_stream_reader(connection_prepared_stream_reader):
    """Create a StreamReader and fill it with an error message."""
    connection_prepared_stream_reader.feed_data(
        b"ERROR: unknown command or variable 'updates'\n"
    )
    connection_prepared_stream_reader.feed_eof()
    return connection_prepared_stream_reader


@pytest.fixture(name="auth_succeeded_prepared_stream_reader")
def fixture_auth_succeeded_prepared_stream_reader(connection_prepared_stream_reader):
    """Create StreamReader and fill it with auth succeeded."""
    connection_prepared_stream_reader.feed_data(b"OK\n")
    return connection_prepared_stream_reader


@pytest.fixture(name="auth_failed_prepared_stream_reader")
def fixture_auth_failed_prepared_stream_reader(connection_prepared_stream_reader):
    """Create StreamReader and fill it with auth succeeded."""
    connection_prepared_stream_reader.feed_data(b"FAILED\n")
    return connection_prepared_stream_reader


@pytest.fixture(name="pyon_options_prepared_stream_reader")
def fixture_pyon_options_prepared_stream_reader(connection_prepared_stream_reader):
    """Create StreamReader and fill it with pyon options."""
    connection_prepared_stream_reader.feed_data(b"> \n")
    connection_prepared_stream_reader.feed_data(b"> \n")
    connection_prepared_stream_reader.feed_data(b"> \n")
    connection_prepared_stream_reader.feed_data(b"> \n")
    connection_prepared_stream_reader.feed_data(b"PyON 1 options\n")
    connection_prepared_stream_reader.feed_data(
        b'{"allow": "127.0.0.1 192.168.0.0/24", "idle": "true", "max-packet-size": "big", "next-unit-percentage": "100", "open-web-control": "true", "passkey": "testkey", "password": "testpassword", "power": "FULL", "proxy": ":8080", "team": "1234456", "user": "testuser"}\n'  # pylint: disable=line-too-long # noqa: line-too-long
    )
    connection_prepared_stream_reader.feed_data(b"---\n")
    connection_prepared_stream_reader.feed_eof()
    return connection_prepared_stream_reader


@pytest.fixture
def patched_open_connection(event_loop):
    """Return a tuple of patched stream_reader and stream_writer."""
    stream_reader = MagicMock()
    stream_writer = MagicMock()
    if asyncio.iscoroutinefunction(stream_reader):
        # Python 3.8.2 and later
        return_value = (stream_reader, stream_writer)
        stream_reader.readuntil.return_value = bytes(10)
    else:
        # Python 3.8.0 and earlier
        return_value = event_loop.create_future()
        return_value.set_result((stream_reader, stream_writer))
        reader_future = event_loop.create_future()
        reader_future.set_result(bytes(10))
        stream_reader.readuntil.return_value = reader_future
    return return_value


@pytest.fixture
def patched_auth_succeeded_open_connection(
    auth_succeeded_prepared_stream_reader, event_loop
):
    """Return a tuple of patched stream_reader and stream_writer."""
    stream_writer = MagicMock()
    if asyncio.iscoroutinefunction(stream_writer):
        # Python 3.8.2 and later
        return_value = (auth_succeeded_prepared_stream_reader, stream_writer)
    else:
        # Python 3.8.0 and earlier
        return_value = event_loop.create_future()
        return_value.set_result((auth_succeeded_prepared_stream_reader, stream_writer))
    return return_value


@pytest.fixture
def patched_auth_failed_open_connection(auth_failed_prepared_stream_reader, event_loop):
    """Return a tuple of patched stream_reader and stream_writer."""
    stream_writer = MagicMock()
    if asyncio.iscoroutinefunction(stream_writer):
        # Python 3.8.2 and later
        return_value = (auth_failed_prepared_stream_reader, stream_writer)
    else:
        # Python 3.8.0 and earlier
        return_value = event_loop.create_future()
        return_value.set_result((auth_failed_prepared_stream_reader, stream_writer))
    return return_value


@pytest.fixture
def patched_error_prepared_open_connection(error_prepared_stream_reader, event_loop):
    """Return a tuple of patched stream_reader and stream_writer."""
    stream_writer = MagicMock()
    if asyncio.iscoroutinefunction(stream_writer):
        # Python 3.8.2 and later
        return_value = (error_prepared_stream_reader, stream_writer)
    else:
        # Python 3.8.0 and earlier
        return_value = event_loop.create_future()
        return_value.set_result((error_prepared_stream_reader, stream_writer))
    return return_value


@pytest.fixture
def patched_pyon_options_prepared_open_connection(
    pyon_options_prepared_stream_reader, event_loop
):
    """Return a tuple of patched stream_reader and stream_writer."""
    stream_writer = MagicMock()
    if asyncio.iscoroutinefunction(stream_writer):
        # Python 3.8.2 and later
        return_value = (pyon_options_prepared_stream_reader, stream_writer)
    else:
        # Python 3.8.0 and earlier
        return_value = event_loop.create_future()
        return_value.set_result((pyon_options_prepared_stream_reader, stream_writer))
    return return_value


@pytest.fixture
def serialconnection():
    """Create a serialconnection."""
    return SerialConnection("localhost", read_timeout=1)
