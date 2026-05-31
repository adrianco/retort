"""Shared pytest fixtures.

We load the production CSVs exactly once per test session (the load is the
slow part, ~1s) and share the resulting DataStore across every test module.
This keeps the suite snappy while still exercising the real, full-size
datasets the spec requires.
"""

from __future__ import annotations

import pytest

from brazilian_soccer_mcp import load_default
from brazilian_soccer_mcp.data_loader import DataStore


@pytest.fixture(scope="session")
def store() -> DataStore:
    return load_default()
