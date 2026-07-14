"""Pytest fixtures.

A single dataset load is shared across the whole test session because
the CSV files together are ~12 MB and parsing them takes ~0.5 s.
"""

from __future__ import annotations

import os
import sys

import pytest

# Make the project importable without installing it.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from brazilian_soccer_mcp import load_dataset  # noqa: E402


@pytest.fixture(scope="session")
def dataset():
    """Load every CSV once for the whole test session."""
    return load_dataset()
