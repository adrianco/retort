import pytest

from tests.acceptance.dsl import SoccerKnowledgeDsl
from tests.acceptance.drivers import McpStdioDriver


@pytest.fixture(scope="session")
def driver():
    d = McpStdioDriver()
    d.start()
    yield d
    d.stop()


@pytest.fixture
def soccer(driver):
    return SoccerKnowledgeDsl(driver)
