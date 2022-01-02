"""Tests for serialconnection"""
import asyncio
from unittest.mock import patch

import pytest

from FoldingAtHomeControl import FoldingAtHomeControlConnectionFailed


async def wait_two_seconds(separator=b"\n"):
    """Waits 2 seconds async than return a single byte."""
    await asyncio.sleep(2)
    return bytes(separator)


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
    assert serialconnection.read_timeout == 1
    serialconnection.set_read_timeout(5)
    assert serialconnection.read_timeout == 5
