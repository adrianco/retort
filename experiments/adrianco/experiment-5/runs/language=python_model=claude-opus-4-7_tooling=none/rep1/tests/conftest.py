"""Shared pytest fixtures.

The DataStore load takes a few seconds, so build it once per session
and reuse it across every test.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from brazilian_soccer_mcp.data_loader import load_all  # noqa: E402
from brazilian_soccer_mcp.queries import SoccerQueries  # noqa: E402


@pytest.fixture(scope="session")
def store():
    return load_all(ROOT / "data" / "kaggle")


@pytest.fixture(scope="session")
def queries(store) -> SoccerQueries:
    return SoccerQueries(store)
