import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from soccer_data import get_database  # noqa: E402


@pytest.fixture(scope="session")
def db():
    """Given the match and player data is loaded."""
    return get_database()
