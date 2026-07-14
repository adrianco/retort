"""Shared pytest fixtures."""
import pathlib

import pytest

FIXTURE_DIR = pathlib.Path(__file__).parent / "fixtures" / "kaggle"
REAL_DATA_DIR = pathlib.Path(__file__).parent.parent / "data" / "kaggle"


@pytest.fixture(scope="session")
def fixture_dir():
    return FIXTURE_DIR


@pytest.fixture(scope="session")
def real_data_dir():
    return REAL_DATA_DIR
