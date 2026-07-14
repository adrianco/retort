"""Shared pytest fixtures.

The knowledge base loads all six CSVs once per test session (Given step for
every scenario: "the match and player data is loaded").
"""

import pytest

from soccer_kb import SoccerKB


@pytest.fixture(scope="session")
def kb() -> SoccerKB:
    return SoccerKB()
