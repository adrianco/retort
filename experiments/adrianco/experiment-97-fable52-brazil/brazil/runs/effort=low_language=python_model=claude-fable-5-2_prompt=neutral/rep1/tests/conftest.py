import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from brazilian_soccer_mcp import load_default  # noqa: E402


@pytest.fixture(scope="session")
def kb():
    """Given the match and player data is loaded."""
    return load_default()
