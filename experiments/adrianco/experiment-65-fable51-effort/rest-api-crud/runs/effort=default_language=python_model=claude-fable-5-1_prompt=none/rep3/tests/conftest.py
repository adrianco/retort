import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app  # noqa: E402


@pytest.fixture
def app(tmp_path):
    application = create_app({"TESTING": True, "DATABASE": str(tmp_path / "test.db")})
    yield application


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def sample_book():
    return {
        "title": "Release It!",
        "author": "Michael Nygard",
        "year": 2018,
        "isbn": "978-1-68050-239-8",
    }
