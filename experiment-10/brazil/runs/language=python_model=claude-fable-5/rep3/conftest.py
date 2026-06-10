"""Shared pytest fixtures: load the database once per test session."""

import pytest

from data_loader import load_database


@pytest.fixture(scope="session")
def db():
    return load_database()
