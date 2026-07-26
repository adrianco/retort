"""Shared pytest fixtures.

Tests run against a private in-memory SQLite database, so they are fast and
leave nothing behind.  The tests that specifically exercise on-disk storage
create their own application inside ``tmp_path``.
"""

from __future__ import annotations

from typing import Any, Dict

import pytest

from book_api import create_app

#: A realistic book used as the baseline payload of most tests.
SAMPLE_BOOK: Dict[str, Any] = {
    "title": "Dune",
    "author": "Frank Herbert",
    "year": 1965,
    "isbn": "978-0-441-01359-3",
}


@pytest.fixture
def app():
    application = create_app({"DATABASE": ":memory:", "TESTING": True})
    yield application


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def create_book(client):
    """Create a book through the API and return the decoded response body."""

    def _create_book(**overrides: Any) -> Dict[str, Any]:
        payload = dict(SAMPLE_BOOK)
        payload.update(overrides)
        response = client.post("/books", json=payload)
        assert response.status_code == 201, response.get_json()
        return response.get_json()

    return _create_book


@pytest.fixture
def library(create_book):
    """A small collection covering filtering, sorting and pagination."""
    return [
        create_book(title="Dune", author="Frank Herbert", year=1965, isbn="9780441013593"),
        create_book(title="Children of Dune", author="Frank Herbert", year=1976, isbn=None),
        create_book(title="Neuromancer", author="William Gibson", year=1984, isbn=None),
        create_book(title="A Wizard of Earthsea", author="Ursula K. Le Guin", year=1968, isbn=None),
    ]
