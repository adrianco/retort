import pytest

from tests.acceptance.dsl import SoccerDsl
from tests.acceptance.mcp_driver import McpProtocolDriver


@pytest.fixture
def soccer():
    return SoccerDsl(McpProtocolDriver())
