"""Tests for foldingathomecontrol"""
import asyncio

try:
    from asyncio.streams import IncompleteReadError  # type: ignore
except ImportError:
    from asyncio import IncompleteReadError  # type: ignore
from asyncio.streams import StreamReader
from unittest.mock import patch

try:
    from unittest.mock import AsyncMock as MagicMock
except ImportError:
    from unittest.mock import MagicMock

    async def async_magic():
        pass

    MagicMock.__await__ = lambda x: async_magic().__await__()

import pytest

from FoldingAtHomeControl import (
    FoldingAtHomeControlAuthenticationFailed,
    FoldingAtHomeControlAuthenticationRequired,
    FoldingAtHomeController,
    FoldingAtHomeControlNotConnected,
    FoldingAtHomeControlConnectionFailed,
)


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


@pytest.fixture
def connection_prepared_stream_reader():
    """Create a StreamReader and fill it with connection messages."""
    reader = StreamReader()
    reader.feed_data(
        b"\x1b[H\x1b[2JWelcome to the Folding@home Client command server.\n"
    )
    return reader


@pytest.fixture
def error_prepared_stream_reader(connection_prepared_stream_reader):
    """Create a StreamReader and fill it with an error message."""
    connection_prepared_stream_reader.feed_data(
        b"ERROR: unknown command or variable 'updates'\n"
    )
    connection_prepared_stream_reader.feed_eof()
    return connection_prepared_stream_reader


@pytest.fixture
def auth_succeeded_prepared_stream_reader(connection_prepared_stream_reader):
    """Create StreamReader and fill it with auth succeeded."""
    connection_prepared_stream_reader.feed_data(b"OK\n")
    return connection_prepared_stream_reader


@pytest.fixture
def auth_failed_prepared_stream_reader(connection_prepared_stream_reader):
    """Create StreamReader and fill it with auth succeeded."""
    connection_prepared_stream_reader.feed_data(b"FAILED\n")
    return connection_prepared_stream_reader


@pytest.fixture
def pyon_options_prepared_stream_reader(connection_prepared_stream_reader):
    """Create StreamReader and fill it with pyon options."""
    connection_prepared_stream_reader.feed_data(b"> \n")
    connection_prepared_stream_reader.feed_data(b"> \n")
    connection_prepared_stream_reader.feed_data(b"> \n")
    connection_prepared_stream_reader.feed_data(b"> \n")
    connection_prepared_stream_reader.feed_data(b"PyON 1 options\n")
    connection_prepared_stream_reader.feed_data(
        b'{"allow": "127.0.0.1 192.168.0.0/24", "idle": "true", "max-packet-size": "big", "next-unit-percentage": "100", "open-web-control": "true", "passkey": "testkey", "password": "testpassword", "power": "FULL", "proxy": ":8080", "team": "1234456", "user": "testuser"}\n'
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


@pytest.mark.asyncio
async def test_request_work_server_assignment_raises_when_not_connected(
    foldingathomecontroller,
):
    """request_work_server_assignment raises exception when client is not connected."""
    with pytest.raises(FoldingAtHomeControlNotConnected):
        await foldingathomecontroller.request_work_server_assignment_async()


@pytest.mark.asyncio
async def test_controller_catches_ConnectionError(
    foldingathomecontroller,
):
    """Test that all Connectionerrors are caught."""
    with patch("asyncio.open_connection", side_effect=ConnectionError()):
        with pytest.raises(FoldingAtHomeControlConnectionFailed):
            await foldingathomecontroller.try_connect_async(timeout=5)


@pytest.mark.asyncio
async def test_controller_disconnects_on_IncompleteReadError(
    disconnecting_foldingathomecontroller, patched_open_connection
):
    """Test that a IncompleteReadError is caught and leads to a reconnect."""
    with patch("asyncio.open_connection", return_value=patched_open_connection):
        await disconnecting_foldingathomecontroller.try_connect_async(timeout=5)
        stream_reader, _ = await asyncio.open_connection("localhost")
        stream_reader.readuntil.side_effect = IncompleteReadError([None], 5)
        await disconnecting_foldingathomecontroller.start(
            connect=False, subscribe=False
        )
        assert not disconnecting_foldingathomecontroller.is_connected


@pytest.mark.asyncio
async def test_controller_calls_on_disconnect_on_IncompleteReadError(
    disconnecting_foldingathomecontroller, patched_open_connection
):
    """Test that a IncompleteReadError is caught and calls on_disconnect()."""
    callback = MagicMock()
    with patch("asyncio.open_connection", return_value=patched_open_connection):
        await disconnecting_foldingathomecontroller.try_connect_async(timeout=5)
        stream_reader, _ = await asyncio.open_connection("localhost")
        stream_reader.readuntil.side_effect = IncompleteReadError([None], 5)
        disconnecting_foldingathomecontroller.on_disconnect(callback)
        await disconnecting_foldingathomecontroller.start(
            connect=False, subscribe=False
        )
        assert not disconnecting_foldingathomecontroller.is_connected
        callback.assert_called()


@pytest.mark.asyncio
async def test_controller_reconnects(foldingathomecontroller, patched_open_connection):
    """Test that the controller reconnects."""
    with patch("asyncio.open_connection", return_value=patched_open_connection):
        await foldingathomecontroller.try_connect_async(timeout=5)
        stream_reader, _ = await asyncio.open_connection("localhost")
        stream_reader.readuntil.side_effect = IncompleteReadError([None], 5)
        task = asyncio.get_event_loop().create_task(
            foldingathomecontroller.start(connect=False, subscribe=False)
        )
        _, pending = await asyncio.wait([task], timeout=0.5)
        assert task in pending
        try:
            task.cancel()
            await task
        except:  # pylint: disable=bare-except # noqa
            pass


@pytest.mark.asyncio
async def test_controller_cleans_up_on_cancel(
    foldingathomecontroller, patched_open_connection
):
    """Test that the controller cleans up."""
    with patch("asyncio.open_connection", return_value=patched_open_connection):
        task = asyncio.ensure_future(foldingathomecontroller.start())
        with pytest.raises(asyncio.CancelledError):
            await asyncio.sleep(0.5)
            task.cancel()
            await task
            assert not foldingathomecontroller.is_connected


@pytest.mark.asyncio
async def test_controller_connects_on_start(
    foldingathomecontroller, patched_open_connection
):
    """Test that the controller connects when start() is called."""
    with patch("asyncio.open_connection", return_value=patched_open_connection):
        task = asyncio.ensure_future(foldingathomecontroller.start())
        await asyncio.sleep(0.5)
        assert foldingathomecontroller.is_connected
        try:
            task.cancel()
            await task
        except:  # pylint: disable=bare-except # noqa
            pass


@pytest.mark.asyncio
async def test_auth_succeeded(
    auth_foldingathomecontroller, patched_auth_succeeded_open_connection
):
    """Test that authenticating works."""
    with patch(
        "asyncio.open_connection", return_value=patched_auth_succeeded_open_connection
    ):
        await auth_foldingathomecontroller.try_connect_async(timeout=5)
        assert auth_foldingathomecontroller.is_connected


@pytest.mark.asyncio
async def test_auth_failed(
    auth_foldingathomecontroller, patched_auth_failed_open_connection
):
    """Test that authenticating works."""
    with patch(
        "asyncio.open_connection", return_value=patched_auth_failed_open_connection
    ):
        with pytest.raises(FoldingAtHomeControlAuthenticationFailed):
            await auth_foldingathomecontroller.try_connect_async(timeout=5)


@pytest.mark.asyncio
async def test_parse_pyon_options(
    disconnecting_foldingathomecontroller, patched_pyon_options_prepared_open_connection
):
    """Test that parsing a pyon message works."""
    with patch(
        "asyncio.open_connection",
        return_value=patched_pyon_options_prepared_open_connection,
    ):
        callback = MagicMock()
        disconnecting_foldingathomecontroller.register_callback(callback)
        await disconnecting_foldingathomecontroller.start()
        callback.assert_called()


@pytest.mark.asyncio
async def test_parse_error(
    disconnecting_foldingathomecontroller, patched_error_prepared_open_connection
):
    """Test that parsing a pyon message works."""
    with patch(
        "asyncio.open_connection", return_value=patched_error_prepared_open_connection
    ):
        callback = MagicMock()
        disconnecting_foldingathomecontroller.register_callback(callback)
        with pytest.raises(FoldingAtHomeControlAuthenticationRequired):
            await disconnecting_foldingathomecontroller.start()
            callback.assert_called()


def test_set_read_timeout(foldingathomecontroller):
    """Test setting the read timeout works."""
    assert foldingathomecontroller.read_timeout == 15
    foldingathomecontroller.set_read_timeout(10)
    assert foldingathomecontroller.read_timeout == 10


@pytest.mark.asyncio
async def test_set_subscription_update_rate(foldingathomecontroller):
    """Test setting the update rate works."""
    assert foldingathomecontroller.update_rate == 5
    await foldingathomecontroller.set_subscription_update_rate_async(10)
    assert foldingathomecontroller.update_rate == 10
