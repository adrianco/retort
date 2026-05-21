import pytest
from data_loader import BrazilianSoccerData


@pytest.fixture(scope="session")
def soccer_data():
    return BrazilianSoccerData()
