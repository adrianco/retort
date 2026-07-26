"""Shared fixtures: every test gets its own throwaway SQLite file."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from bookapi.app import create_app

# No isbn by default: it is unique, so tests that need one pass it explicitly.
SAMPLE = {"title": "Dune", "author": "Frank Herbert", "year": 1965}


@pytest.fixture()
def db_path(tmp_path):
    return tmp_path / "books.db"


@pytest.fixture()
def client(db_path):
    app = create_app(db_path)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def make_book(client):
    """Create a book via the API and return its JSON representation."""

    def _make(**overrides):
        response = client.post("/books", json={**SAMPLE, **overrides})
        assert response.status_code == 201, response.text
        return response.json()

    return _make
