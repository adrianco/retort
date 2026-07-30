"""Shared fixtures: each test gets a fresh app backed by its own SQLite file."""

import pytest

from bookapi import create_app

GATSBY = {
    "title": "The Great Gatsby",
    "author": "F. Scott Fitzgerald",
    "year": 1925,
    "isbn": "9780743273565",
}
EMMA = {"title": "Emma", "author": "Jane Austen", "year": 1815}


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "books.db"


@pytest.fixture
def app(db_path):
    return create_app({"DATABASE": str(db_path), "TESTING": True})


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def add_book(client):
    """Create a book through the API and return its JSON representation."""

    def _add(**overrides):
        payload = {**GATSBY, **overrides}
        response = client.post("/books", json=payload)
        assert response.status_code == 201, response.get_json()
        return response.get_json()

    return _add
