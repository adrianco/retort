from __future__ import annotations

import pytest

from bookapi import create_app


@pytest.fixture()
def app(tmp_path):
    """A fresh application backed by a throwaway SQLite file per test."""
    return create_app({"DATABASE": str(tmp_path / "test-books.db"), "TESTING": True})


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def make_book(client):
    """Create a book via the API and return its serialized representation."""

    def _make(**overrides):
        payload = {
            "title": "The Hobbit",
            "author": "J.R.R. Tolkien",
            "year": 1937,
            "isbn": "978-0-345-33968-3",
        }
        payload.update(overrides)
        response = client.post("/books", json=payload)
        assert response.status_code == 201, response.get_json()
        return response.get_json()

    return _make
