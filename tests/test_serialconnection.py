"""Tests for serialconnection"""
import asyncio
from unittest.mock import patch

import pytest

from FoldingAtHomeControl import FoldingAtHomeControlConnectionFailed
from FoldingAtHomeControl.serialconnection import SerialConnection

try:
    from unittest.mock import AsyncMock as MagicMock
except ImportError:
    from unittest.mock import MagicMock

    async def async_magic():
        pass

    MagicMock.__await__ = lambda x: async_magic().__await__()


async def wait_two_seconds():
    await asyncio.sleep(2)


@pytest.fixture
def serialconnection():
    """Create a serialconnection."""
    serialconnection = SerialConnection("localhost", read_timeout=0.5)
    return serialconnection


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
        reader_future = event_loop.create_future()
        reader_future.set_result(bytes(10))
        stream_reader.readuntil.return_value = reader_future
        return_value = event_loop.create_future()
        return_value.set_result((stream_reader, stream_writer))
    return return_value


@pytest.mark.asyncio
async def test_read_raises_after_timeout(serialconnection, patched_open_connection):
    """Test that the connection disconnects after the allotted timeout"""
    with patch("asyncio.open_connection", return_value=patched_open_connection):
        await serialconnection.connect_async()
        stream_reader, _ = await asyncio.open_connection("localhost")
        stream_reader.readuntil = wait_two_seconds
        with pytest.raises(FoldingAtHomeControlConnectionFailed):
            await serialconnection.read_async()
            assert not serialconnection.is_connected


def test_set_read_timeout(serialconnection):
    """Test setting the read timeout works."""
    assert serialconnection.read_timeout == 0.5
    serialconnection.set_read_timeout(5)
    assert serialconnection.read_timeout == 5
