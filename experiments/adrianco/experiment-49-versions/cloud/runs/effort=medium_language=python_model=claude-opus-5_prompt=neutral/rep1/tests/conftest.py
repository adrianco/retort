import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """A TestClient backed by a throwaway SQLite file, fresh per test."""
    monkeypatch.setenv("BOOKS_DB_PATH", str(tmp_path / "test-books.db"))

    from bookapi.main import app

    # The lifespan handler runs init_db() against the patched path.
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def sample_book():
    return {
        "title": "The Left Hand of Darkness",
        "author": "Ursula K. Le Guin",
        "year": 1969,
        "isbn": "978-0-441-47812-5",
    }
