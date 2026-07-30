"""Shared pytest fixtures.

Each test gets a brand-new application backed by its own SQLite file inside
pytest's ``tmp_path``, so tests are fully isolated and can run in any order.
"""

from __future__ import annotations

import pytest

from bookapi import create_app

from .samples import SAMPLE_BOOKS


@pytest.fixture
def app(tmp_path):
    """A configured application using a throwaway on-disk database."""
    return create_app({"DATABASE": str(tmp_path / "books.db"), "TESTING": True})


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def book(client):
    """One persisted book, returned as the API represents it."""
    response = client.post("/books", json=SAMPLE_BOOKS[0])
    assert response.status_code == 201, response.get_json()
    return response.get_json()


@pytest.fixture
def library(client):
    """Three persisted books, two of which share an author."""
    created = []
    for payload in SAMPLE_BOOKS:
        response = client.post("/books", json=payload)
        assert response.status_code == 201, response.get_json()
        created.append(response.get_json())
    return created
