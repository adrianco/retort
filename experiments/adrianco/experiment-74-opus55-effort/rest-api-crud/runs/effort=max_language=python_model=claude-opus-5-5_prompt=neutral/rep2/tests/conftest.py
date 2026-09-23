"""Shared fixtures: every test gets an application backed by its own SQLite file."""

import pytest
from fastapi.testclient import TestClient

from books_api.app import create_app


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "books.db"


@pytest.fixture
def client(db_path):
    # Entering the client runs the app's startup, as a real server would.
    with TestClient(create_app(db_path)) as test_client:
        yield test_client


@pytest.fixture
def add_book(client):
    """Create a book through the API and return its JSON. Fields default to Dune."""

    def add(**fields):
        payload = {
            "title": "Dune",
            "author": "Frank Herbert",
            "year": 1965,
            "isbn": "978-0441172719",
            **fields,
        }
        response = client.post("/books", json=payload)
        assert response.status_code == 201, response.text
        return response.json()

    return add
