"""Wires the four layers together: specs -> DSL -> protocol drivers -> the MCP server.

Each spec owns its own archive of synthetic data and its own server instance, so specs
cannot see each other's matches or players (functional isolation) and can run in any order.
The server is started lazily, after the spec has finished describing the archive.
"""
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.acceptance.drivers.archive_driver import ArchiveDriver
from tests.acceptance.drivers.mcp_connection import McpConnection
from tests.acceptance.drivers import soccer_drivers as drivers
from tests.acceptance.dsl.archive import Archive
from tests.acceptance.dsl import questions

PROVIDED_DATA = Path(__file__).resolve().parents[2] / "data" / "kaggle"


class Session:
    def __init__(self, data_directory, archive_driver=None):
        self._data_directory = data_directory
        self._archive_driver = archive_driver
        self._connection = None

    def connection(self):
        if self._connection is None:
            if self._archive_driver:
                self._archive_driver.publish()
            self._connection = McpConnection(self._data_directory)
            self._connection.start()
        return self._connection

    def close(self):
        if self._connection:
            self._connection.close()


def question_areas(session):
    areas = SimpleNamespace(
        matches=questions.Matches(drivers.MatchesDriver(session)),
        teams=questions.Teams(drivers.TeamsDriver(session)),
        rivalries=questions.Rivalries(drivers.RivalriesDriver(session)),
        players=questions.Players(drivers.PlayersDriver(session)),
        competitions=questions.Competitions(drivers.CompetitionsDriver(session)),
        statistics=questions.Statistics(drivers.StatisticsDriver(session)),
    )
    areas.assistant = questions.Assistant(drivers.AssistantDriver(session), areas)
    return areas


@pytest.fixture
def archive_driver(tmp_path):
    return ArchiveDriver(tmp_path)


@pytest.fixture
def session(tmp_path, archive_driver):
    session = Session(tmp_path, archive_driver)
    yield session
    session.close()


@pytest.fixture
def archive(archive_driver):
    return Archive(archive_driver)


@pytest.fixture
def areas(session):
    return question_areas(session)


@pytest.fixture
def matches(areas):
    return areas.matches


@pytest.fixture
def teams(areas):
    return areas.teams


@pytest.fixture
def rivalries(areas):
    return areas.rivalries


@pytest.fixture
def players(areas):
    return areas.players


@pytest.fixture
def competitions(areas):
    return areas.competitions


@pytest.fixture
def statistics(areas):
    return areas.statistics


@pytest.fixture
def assistant(areas):
    return areas.assistant


@pytest.fixture(scope="session")
def provided_session():
    session = Session(PROVIDED_DATA)
    yield session
    session.close()


@pytest.fixture
def provided(provided_session):
    """The same question areas, answered from the real provided datasets (read-only, so shared)."""
    return question_areas(provided_session)
