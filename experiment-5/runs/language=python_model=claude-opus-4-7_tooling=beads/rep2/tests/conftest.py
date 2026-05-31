"""Pytest fixtures shared across BDD and unit tests.

The :func:`data` fixture loads every CSV exactly once per test session — the
combined frames hold ~24k matches and ~18k players, which still loads in a
second or two but makes a per-test reload wasteful.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from soccer_mcp.data import SoccerData  # noqa: E402


@pytest.fixture(scope="session")
def data() -> SoccerData:
    return SoccerData.load(ROOT / "data" / "kaggle")
