"""Shared pytest fixtures for the BDD suite.

The full Kaggle corpus is loaded exactly once per test session so the
scenarios can share an in-memory ``DataStore`` without paying the ~24k row
parse cost on every test.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Make ``src/`` importable without an installation step.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from soccer_mcp.data_loader import DataStore, load_default_store  # noqa: E402


@pytest.fixture(scope="session")
def store() -> DataStore:
    """Session-scoped data store, populated from ``data/kaggle/``."""
    return load_default_store(ROOT / "data" / "kaggle")


@pytest.fixture
def bdd_context() -> dict:
    """Per-scenario scratchpad shared between Given/When/Then steps."""
    return {}
