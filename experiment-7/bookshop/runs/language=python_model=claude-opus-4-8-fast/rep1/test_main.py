"""Integration tests for the Book Collection API."""

import os
import tempfile

import pytest
from fastapi.testclient import TestClient

from main import create_app


@pytest.fixture
def client():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    app = create_app(db_path=path)
    with TestClient(app) as c:
        yield c
    os.remove(path)


def _sample(**overrides):
    book = {
        "title": "The Pragmatic Programmer",
        "author": "Andrew Hunt",
        "year": 1999,
        "isbn": "978-0201616224",
    }
    book.update(overrides)
    return book


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_create_and_get_book(client):
    resp = client.post("/books", json=_sample())
    assert resp.status_code == 201
    created = resp.json()
    assert created["id"] > 0
    assert created["title"] == "The Pragmatic Programmer"

    resp = client.get(f"/books/{created['id']}")
    assert resp.status_code == 200
    assert resp.json() == created


def test_create_requires_title_and_author(client):
    resp = client.post("/books", json={"author": "Someone"})
    assert resp.status_code == 422

    resp = client.post("/books", json={"title": "A Book"})
    assert resp.status_code == 422

    resp = client.post("/books", json=_sample(title="   "))
    assert resp.status_code == 422


def test_list_and_filter_by_author(client):
    client.post("/books", json=_sample(title="Book A", author="Alice"))
    client.post("/books", json=_sample(title="Book B", author="Bob"))
    client.post("/books", json=_sample(title="Book C", author="Alice"))

    resp = client.get("/books")
    assert resp.status_code == 200
    assert len(resp.json()) == 3

    resp = client.get("/books", params={"author": "Alice"})
    assert resp.status_code == 200
    titles = sorted(b["title"] for b in resp.json())
    assert titles == ["Book A", "Book C"]


def test_update_book(client):
    created = client.post("/books", json=_sample()).json()
    resp = client.put(
        f"/books/{created['id']}",
        json=_sample(title="Updated Title", year=2020),
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "Updated Title"
    assert resp.json()["year"] == 2020


def test_update_missing_book_returns_404(client):
    resp = client.put("/books/9999", json=_sample())
    assert resp.status_code == 404


def test_delete_book(client):
    created = client.post("/books", json=_sample()).json()
    resp = client.delete(f"/books/{created['id']}")
    assert resp.status_code == 204

    resp = client.get(f"/books/{created['id']}")
    assert resp.status_code == 404


def test_get_missing_book_returns_404(client):
    resp = client.get("/books/9999")
    assert resp.status_code == 404
