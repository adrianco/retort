import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from brazilian_soccer import load_default  # noqa: E402
from brazilian_soccer.server import call_tool  # noqa: E402


@pytest.fixture(scope="session")
def db():
    """Given the match and player data is loaded."""
    return load_default()


@pytest.fixture(scope="session")
def ask(db):
    """Call an MCP tool the way a client would and return its text answer."""
    return lambda tool, **arguments: call_tool(tool, arguments, db)
