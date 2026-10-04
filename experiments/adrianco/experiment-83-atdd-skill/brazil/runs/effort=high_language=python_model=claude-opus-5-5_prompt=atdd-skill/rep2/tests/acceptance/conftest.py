"""
Wiring for the acceptance tests: gives each spec a DSL connected to its own
protocol drivers.

  soccer   - a fresh, empty set of datasets in a private directory and a
             private server instance, so every spec owns all of its data
             (functional isolation) and specs can run in parallel.
  provided - one shared, read-only server over the real Kaggle datasets in
             data/kaggle, for specs about the provided data.
"""
import pathlib

import pytest

from .drivers.datasets import DatasetsDriver
from .drivers.soccer_server import SoccerServerDriver
from .dsl import SoccerDsl

PROVIDED_DATA = pathlib.Path(__file__).resolve().parents[2] / "data" / "kaggle"


@pytest.fixture
def soccer(tmp_path):
    datasets = DatasetsDriver(tmp_path)
    server = SoccerServerDriver(tmp_path, before_start=datasets.write)
    yield SoccerDsl(server, datasets)
    server.stop()


@pytest.fixture(scope="session")
def provided():
    server = SoccerServerDriver(PROVIDED_DATA)
    yield SoccerDsl(server)
    server.stop()
