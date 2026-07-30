"""Shared pytest fixtures.

Living at the repo root, this file also puts the root on ``sys.path`` so
``import bookapi`` works without installing the package.
"""

from __future__ import annotations

import pytest

from bookapi import create_app

SAMPLE_BOOK = {
    "title": "The Left Hand of Darkness",
    "author": "Ursula K. Le Guin",
    "year": 1969,
    "isbn": "9780441478125",
}


@pytest.fixture
def db_path(tmp_path):
    """A real SQLite file per test.

    Not ``:memory:``: each request opens its own connection, and separate
    in-memory connections would be separate databases.
    """
    return tmp_path / "books.db"


@pytest.fixture
def app(db_path):
    return create_app({"DATABASE": str(db_path), "TESTING": True})


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def created_book(client):
    """One book already in the collection."""
    response = client.post("/books", json=SAMPLE_BOOK)
    assert response.status_code == 201
    return response.get_json()
