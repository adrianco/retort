"""Shared fixtures: the real Kaggle dataset is loaded once per test session."""

import asyncio
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from soccer_mcp.loader import load_dataset  # noqa: E402
from soccer_mcp.queries import SoccerQueries  # noqa: E402
from soccer_mcp.server import create_server  # noqa: E402


@pytest.fixture(scope="session")
def dataset():
    """Given the match and player data is loaded."""
    return load_dataset(ROOT / "data" / "kaggle")


@pytest.fixture(scope="session")
def queries(dataset):
    return SoccerQueries(dataset)


@pytest.fixture(scope="session")
def server(dataset):
    return create_server(dataset=dataset)


@pytest.fixture(scope="session")
def call(server):
    """Call an MCP tool by name and return its text output."""
    def _call(name, **arguments):
        result = asyncio.run(server.call_tool(name, arguments))
        content = result[0] if isinstance(result, tuple) else result
        return content[0].text
    return _call
