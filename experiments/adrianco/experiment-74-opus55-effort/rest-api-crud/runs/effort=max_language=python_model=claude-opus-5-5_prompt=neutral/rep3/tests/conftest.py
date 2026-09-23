"""Shared fixtures: every test gets its own app backed by a fresh SQLite file."""

import pytest

from bookapi import create_app

DUNE = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593"}


@pytest.fixture
def app(tmp_path):
    return create_app({"TESTING": True, "DATABASE": str(tmp_path / "books.db")})


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def create_book(client):
    """POST a book (Dune, unless fields are overridden) and return its JSON."""

    def create(**fields):
        response = client.post("/books", json={**DUNE, **fields})
        assert response.status_code == 201, response.get_json()
        return response.get_json()

    return create
