"""Shared fixtures: each test gets a fresh app backed by its own SQLite file."""

from __future__ import annotations

import pytest

from bookapi import create_app

ORWELL = {"title": "Nineteen Eighty-Four", "author": "George Orwell", "year": 1949,
          "isbn": "9780451524935"}
HUXLEY = {"title": "Brave New World", "author": "Aldous Huxley", "year": 1932,
          "isbn": "9780060850524"}
ORWELL_2 = {"title": "Animal Farm", "author": "George Orwell", "year": 1945}


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "books.db"


@pytest.fixture
def app(db_path):
    return create_app({"TESTING": True, "DATABASE": str(db_path)})


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def create_book(client):
    """POST a book and return its representation, asserting it was created."""

    def _create(payload=None, **overrides):
        body = dict(payload or ORWELL)
        body.update(overrides)
        response = client.post("/books", json=body)
        assert response.status_code == 201, response.get_json()
        return response.get_json()

    return _create
