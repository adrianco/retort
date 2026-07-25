"""Shared pytest fixtures.

Each test gets its own SQLite file inside pytest's ``tmp_path`` so tests are
fully isolated from one another and from any development database.
"""

from __future__ import annotations

import pytest

from app import create_app

SAMPLE_BOOK = {
    "title": "The Left Hand of Darkness",
    "author": "Ursula K. Le Guin",
    "year": 1969,
    "isbn": "9780441478125",
}


@pytest.fixture
def database_path(tmp_path):
    return str(tmp_path / "books.db")


@pytest.fixture
def app(database_path):
    return create_app({"DATABASE": database_path, "TESTING": True})


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def created_book(client):
    """A book that already exists in the collection."""
    response = client.post("/books", json=SAMPLE_BOOK)
    assert response.status_code == 201
    return response.get_json()
