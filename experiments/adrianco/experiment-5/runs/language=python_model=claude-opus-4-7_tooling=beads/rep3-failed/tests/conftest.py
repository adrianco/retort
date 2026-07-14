"""Shared fixtures.

The full CSV load is multi-second; we cache it as a module-scoped fixture
so the whole test session pays the cost once.
"""

import pytest

from brazilian_soccer_mcp.knowledge import SoccerKnowledge


@pytest.fixture(scope="session")
def knowledge() -> SoccerKnowledge:
    return SoccerKnowledge.from_dir("data/kaggle")
