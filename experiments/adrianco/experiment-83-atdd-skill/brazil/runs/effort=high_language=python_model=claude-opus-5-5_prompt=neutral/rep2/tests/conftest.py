import pytest

from data_loader import get_data
from queries import SoccerQueries


@pytest.fixture(scope="session")
def data():
    return get_data()


@pytest.fixture(scope="session")
def q(data):
    return SoccerQueries(data)
