"""Shared pytest fixtures.

Each test gets a brand-new SQLite file inside pytest's ``tmp_path`` so tests
are fully isolated and never touch a developer's real database.
"""

from __future__ import annotations

import pytest

from bookapi import create_app
from sample_data import SAMPLE_BOOK


@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "books.db")


@pytest.fixture
def app(db_path):
    return create_app({"TESTING": True, "DATABASE": db_path})


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def make_book(client):
    """Create a book through the API and return the response body."""

    def _make_book(**overrides):
        payload = {**SAMPLE_BOOK, **overrides}
        response = client.post("/books", json=payload)
        assert response.status_code == 201, response.get_data(as_text=True)
        return response.get_json()

    return _make_book
