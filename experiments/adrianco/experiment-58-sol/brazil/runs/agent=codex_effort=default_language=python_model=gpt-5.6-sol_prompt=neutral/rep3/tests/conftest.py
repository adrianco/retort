from __future__ import annotations

import pytest

from brazilian_soccer_mcp import SoccerRepository, SoccerService
from brazilian_soccer_mcp.query import NaturalLanguageQuery


@pytest.fixture(scope="session")
def repository() -> SoccerRepository:
    return SoccerRepository()


@pytest.fixture(scope="session")
def service(repository: SoccerRepository) -> SoccerService:
    return SoccerService(repository)


@pytest.fixture(scope="session")
def natural_query(service: SoccerService) -> NaturalLanguageQuery:
    return NaturalLanguageQuery(service)

