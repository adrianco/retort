import pytest
from soccer_mcp import load_all, QueryEngine


@pytest.fixture(scope="session")
def datasets():
    return load_all()


@pytest.fixture(scope="session")
def engine(datasets):
    return QueryEngine(datasets)
