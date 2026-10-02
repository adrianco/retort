"""
Wires the four layers together for pytest.

Each synthetic-data spec gets its own dataset directory and its own server
process, so specs are functionally isolated and can run in any order. The
dataset is written just before the first question is asked, which lets the
"given" steps accumulate facts first. The provided-data specs share one
server over the real Kaggle files, since that data is read-only.
"""

from pathlib import Path

import pytest

from .drivers.kaggle_files import KaggleFiles
from .drivers.mcp_driver import McpSoccerDriver
from .dsl.competitions import Competitions
from .dsl.dataset import Dataset
from .dsl.matches import Matches
from .dsl.players import Players
from .dsl.provided_data import ProvidedData
from .dsl.statistics import Statistics
from .dsl.teams import Teams

PROVIDED_DATA = Path(__file__).resolve().parents[2] / "data" / "kaggle"


@pytest.fixture
def kaggle_files(tmp_path):
    return KaggleFiles(tmp_path / "kaggle")


@pytest.fixture
def driver(kaggle_files):
    driver = McpSoccerDriver(kaggle_files.directory, before_first_question=kaggle_files.write)
    yield driver
    driver.close()


@pytest.fixture
def given(kaggle_files):
    return Dataset(kaggle_files)


@pytest.fixture
def matches(driver):
    return Matches(driver)


@pytest.fixture
def teams(driver):
    return Teams(driver)


@pytest.fixture
def players(driver):
    return Players(driver)


@pytest.fixture
def competitions(driver):
    return Competitions(driver)


@pytest.fixture
def statistics(driver):
    return Statistics(driver)


@pytest.fixture(scope="session")
def provided_data_driver():
    driver = McpSoccerDriver(PROVIDED_DATA)
    yield driver
    driver.close()


@pytest.fixture
def real_data(provided_data_driver):
    return ProvidedData(provided_data_driver)
