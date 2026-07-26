import pytest

from books import create_app


@pytest.fixture
def app(tmp_path):
    """A fresh app backed by a throwaway SQLite file per test."""
    return create_app({"TESTING": True, "DATABASE": str(tmp_path / "test.sqlite3")})


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def make_book(client):
    """Create a book via the API and return its JSON representation."""

    def _make(**overrides):
        payload = {"title": "Dune", "author": "Frank Herbert", "year": 1965}
        payload.update(overrides)
        response = client.post("/books", json=payload)
        assert response.status_code == 201, response.get_json()
        return response.get_json()

    return _make
