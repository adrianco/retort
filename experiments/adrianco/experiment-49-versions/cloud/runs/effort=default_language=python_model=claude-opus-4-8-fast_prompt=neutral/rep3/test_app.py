"""Integration tests for the Book Collection API."""

import os
import tempfile

import pytest

from app import create_app


@pytest.fixture()
def client():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    app = create_app(db_path=path)
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c
    os.remove(path)


def _make_book(client, **overrides):
    payload = {
        "title": "The Pragmatic Programmer",
        "author": "Andrew Hunt",
        "year": 1999,
        "isbn": "978-0201616224",
    }
    payload.update(overrides)
    return client.post("/books", json=payload)


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_create_and_get_book(client):
    resp = _make_book(client)
    assert resp.status_code == 201
    book = resp.get_json()
    assert book["id"] > 0
    assert book["title"] == "The Pragmatic Programmer"
    assert book["author"] == "Andrew Hunt"

    get_resp = client.get(f"/books/{book['id']}")
    assert get_resp.status_code == 200
    assert get_resp.get_json() == book


def test_create_book_validation_requires_title_and_author(client):
    assert client.post("/books", json={"author": "Someone"}).status_code == 400
    assert client.post("/books", json={"title": "", "author": "Someone"}).status_code == 400
    assert client.post("/books", json={"title": "  ", "author": "Someone"}).status_code == 400
    assert client.post("/books", json={"title": "A Title"}).status_code == 400


def test_list_books_with_author_filter(client):
    _make_book(client, title="Book A", author="Alice")
    _make_book(client, title="Book B", author="Bob")
    _make_book(client, title="Book C", author="Alice")

    all_books = client.get("/books").get_json()
    assert len(all_books) == 3

    alice_books = client.get("/books?author=Alice").get_json()
    assert len(alice_books) == 2
    assert all(b["author"] == "Alice" for b in alice_books)


def test_update_book(client):
    book = _make_book(client).get_json()
    resp = client.put(
        f"/books/{book['id']}",
        json={"title": "Updated", "author": "New Author", "year": 2020, "isbn": None},
    )
    assert resp.status_code == 200
    updated = resp.get_json()
    assert updated["title"] == "Updated"
    assert updated["author"] == "New Author"
    assert updated["year"] == 2020
    assert updated["isbn"] is None


def test_delete_book(client):
    book = _make_book(client).get_json()
    assert client.delete(f"/books/{book['id']}").status_code == 204
    assert client.get(f"/books/{book['id']}").status_code == 404


def test_get_missing_book_returns_404(client):
    assert client.get("/books/9999").status_code == 404


def test_update_missing_book_returns_404(client):
    resp = client.put(
        "/books/9999",
        json={"title": "X", "author": "Y", "year": None, "isbn": None},
    )
    assert resp.status_code == 404


def test_delete_missing_book_returns_404(client):
    assert client.delete("/books/9999").status_code == 404
