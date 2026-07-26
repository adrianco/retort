"""Shared fixtures. Each test gets a fresh app backed by its own SQLite file."""

from __future__ import annotations

from typing import Any

import pytest

from bookapi import create_app


@pytest.fixture
def db_path(tmp_path):
    """Path to a throwaway database file, unique per test."""
    return str(tmp_path / "books.db")


@pytest.fixture
def app(db_path):
    return create_app({"TESTING": True, "DATABASE": db_path})


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def add_book(client):
    """Create a book through the API and return the created resource.

    ISBNs are generated per call so tests that create several books do not trip
    the uniqueness constraint by accident.
    """
    counter = {"n": 0}

    def _add(**overrides: Any) -> dict[str, Any]:
        counter["n"] += 1
        payload: dict[str, Any] = {
            "title": f"Book {counter['n']}",
            "author": "George Orwell",
            "year": 1949,
            "isbn": f"978000000{counter['n']:04d}",
        }
        payload.update(overrides)

        response = client.post("/books", json=payload)
        assert response.status_code == 201, response.get_json()
        return response.get_json()

    return _add
