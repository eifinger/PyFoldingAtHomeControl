"""Tests for foldingathomecontrol"""
import pytest
from FoldingAtHomeControl import FoldingAtHomeController, FoldingAtHomeControlNotConnected


@pytest.fixture
def foldingathomecontroller():
    """Create a localhost FoldingAtHomeController."""
    return FoldingAtHomeController("localhost")


@pytest.mark.asyncio
async def test_request_work_server_assignment_raises_when_not_connected(foldingathomecontroller):
    """request_work_server_assignment raises exception when client is not connected."""
    with pytest.raises(FoldingAtHomeControlNotConnected):
        await foldingathomecontroller.request_work_server_assignment()
