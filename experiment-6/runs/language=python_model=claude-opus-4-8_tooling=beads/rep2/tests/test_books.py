"""Integration tests for the Book Collection API."""

import os
import tempfile

import pytest
from fastapi.testclient import TestClient

from app import db
from app.main import app


@pytest.fixture()
def client():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db.set_db_path(path)
    db.init_db()
    with TestClient(app) as c:
        yield c
    os.unlink(path)


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_create_and_get_book(client):
    resp = client.post(
        "/books",
        json={"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "12345"},
    )
    assert resp.status_code == 201
    book = resp.json()
    assert book["id"] > 0
    assert book["title"] == "Dune"

    get_resp = client.get(f"/books/{book['id']}")
    assert get_resp.status_code == 200
    assert get_resp.json()["author"] == "Frank Herbert"


def test_missing_required_fields_returns_422(client):
    resp = client.post("/books", json={"title": "No Author"})
    assert resp.status_code == 422

    resp = client.post("/books", json={"title": "  ", "author": "  "})
    assert resp.status_code == 422


def test_list_and_author_filter(client):
    client.post("/books", json={"title": "A", "author": "Alice"})
    client.post("/books", json={"title": "B", "author": "Bob"})
    client.post("/books", json={"title": "C", "author": "Alice"})

    all_books = client.get("/books").json()
    assert len(all_books) == 3

    alice_books = client.get("/books", params={"author": "Alice"}).json()
    assert len(alice_books) == 2
    assert {b["title"] for b in alice_books} == {"A", "C"}


def test_update_book(client):
    created = client.post("/books", json={"title": "Old", "author": "X"}).json()
    resp = client.put(
        f"/books/{created['id']}",
        json={"title": "New", "author": "Y", "year": 2000, "isbn": "999"},
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "New"
    assert resp.json()["year"] == 2000


def test_delete_book(client):
    created = client.post("/books", json={"title": "Temp", "author": "Z"}).json()
    resp = client.delete(f"/books/{created['id']}")
    assert resp.status_code == 204
    assert client.get(f"/books/{created['id']}").status_code == 404


def test_get_missing_book_returns_404(client):
    assert client.get("/books/99999").status_code == 404
    assert client.put("/books/99999", json={"title": "T", "author": "A"}).status_code == 404
    assert client.delete("/books/99999").status_code == 404
