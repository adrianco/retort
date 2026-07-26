import pytest

from app import create_app


@pytest.fixture
def client(tmp_path):
    """A test client backed by a throwaway SQLite file, fresh per test."""
    app = create_app(database=str(tmp_path / "test.db"))
    app.config.update(TESTING=True)
    with app.test_client() as client:
        yield client


@pytest.fixture
def sample_book():
    return {
        "title": "The Pragmatic Programmer",
        "author": "Andrew Hunt",
        "year": 1999,
        "isbn": "978-0-201-61622-4",
    }
