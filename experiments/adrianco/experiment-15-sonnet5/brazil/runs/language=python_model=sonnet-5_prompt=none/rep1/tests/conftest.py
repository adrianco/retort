import pytest

from soccer_mcp.data_loader import load_all
from soccer_mcp.repository import SoccerRepository


@pytest.fixture(scope="session")
def repo():
    return SoccerRepository(load_all())
