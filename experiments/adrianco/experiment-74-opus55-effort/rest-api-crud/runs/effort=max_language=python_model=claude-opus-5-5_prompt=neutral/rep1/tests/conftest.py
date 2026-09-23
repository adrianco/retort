"""Fixtures shared by the test suite."""

import pytest

from app import create_app


@pytest.fixture
def app(tmp_path):
    """A fresh application backed by its own temporary SQLite database."""
    return create_app({"TESTING": True, "DATABASE": tmp_path / "books.db"})


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def add_book(client):
    """Create a book through the API and return it as the API reported it."""

    def add(**fields):
        payload = {"title": "Dune", "author": "Frank Herbert", "year": 1965, **fields}
        response = client.post("/books", json=payload)
        assert response.status_code == 201, response.get_json()
        return response.get_json()

    return add
