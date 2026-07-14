"""Shared pytest fixtures.

Loads the dataset exactly once per test session so the BDD scenarios feel
snappy. Tests are written in a Given/When/Then style with helper functions
that read like English to keep scenarios self-documenting.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from brazilian_soccer_mcp.data_loader import DataStore, load_all  # noqa: E402


@pytest.fixture(scope="session")
def store() -> DataStore:
    return load_all()
