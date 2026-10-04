import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from brsoccer.data import get_db  # noqa: E402


@pytest.fixture(scope="session")
def db():
    return get_db()
