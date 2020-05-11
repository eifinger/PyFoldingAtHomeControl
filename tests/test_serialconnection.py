"""Tests for serialconnection"""
import asyncio
from unittest.mock import MagicMock, patch

import pytest

from FoldingAtHomeControl import FoldingAtHomeControlConnectionFailed
from FoldingAtHomeControl.serialconnection import SerialConnection


async def async_magic():
    pass


async def wait_two_seconds():
    await asyncio.sleep(2)


MagicMock.__await__ = lambda x: async_magic().__await__()


@pytest.fixture
def serialconnection():
    """Create a serialconnection."""
    serialconnection = SerialConnection("localhost", read_timeout=0.5)
    return serialconnection


@pytest.mark.asyncio
async def test_read_raises_after_timeout(serialconnection):
    """Test that the connection disconnects after the allotted timeout"""
    stream_reader = MagicMock()
    reader_future = asyncio.Future()
    reader_future.set_result(bytes(10))
    stream_reader.readuntil.return_value = reader_future
    stream_writer = MagicMock()
    future = asyncio.Future()
    future.set_result((stream_reader, stream_writer))
    with patch("asyncio.open_connection", return_value=future):
        await serialconnection.connect_async()
        stream_reader.readuntil = wait_two_seconds
        with pytest.raises(FoldingAtHomeControlConnectionFailed):
            await serialconnection.read_async()
            assert not serialconnection.is_connected


def test_set_read_timeout(serialconnection):
    """Test setting the read timeout works."""
    assert serialconnection.read_timeout == 0.5
    serialconnection.set_read_timeout(5)
    assert serialconnection.read_timeout == 5
