"""Integration tests for the books REST API."""

from __future__ import annotations

import os
import tempfile

import pytest

from app import create_app


@pytest.fixture()
def client():
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        app = create_app(db_path=db_path)
        app.config.update(TESTING=True)
        with app.test_client() as c:
            yield c
    finally:
        try:
            os.unlink(db_path)
        except FileNotFoundError:
            pass


def _make_book(client, **overrides):
    payload = {
        "title": "The Pragmatic Programmer",
        "author": "Andy Hunt",
        "year": 1999,
        "isbn": "978-0201616224",
    }
    payload.update(overrides)
    return client.post("/books", json=payload)


def test_health_endpoint(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_create_and_get_book(client):
    resp = _make_book(client)
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["id"] >= 1
    assert body["title"] == "The Pragmatic Programmer"
    assert body["author"] == "Andy Hunt"
    assert body["year"] == 1999
    assert body["isbn"] == "978-0201616224"

    got = client.get(f"/books/{body['id']}")
    assert got.status_code == 200
    assert got.get_json() == body


def test_create_book_requires_title_and_author(client):
    # Missing title
    resp = client.post("/books", json={"author": "Someone"})
    assert resp.status_code == 400
    assert "title" in resp.get_json()["error"]

    # Missing author
    resp = client.post("/books", json={"title": "Book"})
    assert resp.status_code == 400
    assert "author" in resp.get_json()["error"]

    # Empty title (whitespace)
    resp = client.post("/books", json={"title": "  ", "author": "X"})
    assert resp.status_code == 400

    # Wrong content-type / not JSON
    resp = client.post("/books", data="not json", content_type="text/plain")
    assert resp.status_code == 400

    # Bad year type
    resp = client.post(
        "/books",
        json={"title": "T", "author": "A", "year": "nineteen"},
    )
    assert resp.status_code == 400


def test_list_books_and_author_filter(client):
    _make_book(client, title="Book A", author="Alice")
    _make_book(client, title="Book B", author="Bob")
    _make_book(client, title="Book C", author="Alice")

    resp = client.get("/books")
    assert resp.status_code == 200
    all_books = resp.get_json()
    assert len(all_books) == 3

    resp = client.get("/books?author=Alice")
    assert resp.status_code == 200
    alice_books = resp.get_json()
    assert len(alice_books) == 2
    assert {b["title"] for b in alice_books} == {"Book A", "Book C"}
    assert all(b["author"] == "Alice" for b in alice_books)

    resp = client.get("/books?author=NoSuchAuthor")
    assert resp.status_code == 200
    assert resp.get_json() == []


def test_update_book(client):
    created = _make_book(client).get_json()
    bid = created["id"]

    # Partial update
    resp = client.put(f"/books/{bid}", json={"year": 2000})
    assert resp.status_code == 200
    updated = resp.get_json()
    assert updated["year"] == 2000
    assert updated["title"] == created["title"]  # unchanged
    assert updated["author"] == created["author"]

    # Full update
    resp = client.put(
        f"/books/{bid}",
        json={"title": "New Title", "author": "New Author", "year": 2020, "isbn": "111"},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["title"] == "New Title"
    assert body["author"] == "New Author"
    assert body["year"] == 2020
    assert body["isbn"] == "111"

    # Invalid update — empty title
    resp = client.put(f"/books/{bid}", json={"title": ""})
    assert resp.status_code == 400

    # Empty body
    resp = client.put(f"/books/{bid}", json={})
    assert resp.status_code == 400

    # Non-existent book
    resp = client.put("/books/99999", json={"title": "X"})
    assert resp.status_code == 404


def test_delete_book(client):
    created = _make_book(client).get_json()
    bid = created["id"]

    resp = client.delete(f"/books/{bid}")
    assert resp.status_code == 204
    assert resp.data == b""

    # Second delete → 404
    resp = client.delete(f"/books/{bid}")
    assert resp.status_code == 404

    # Get after delete → 404
    resp = client.get(f"/books/{bid}")
    assert resp.status_code == 404


def test_get_nonexistent_book(client):
    resp = client.get("/books/42")
    assert resp.status_code == 404
    assert "error" in resp.get_json()


def test_unknown_field_rejected(client):
    resp = client.post(
        "/books",
        json={"title": "T", "author": "A", "publisher": "P"},
    )
    assert resp.status_code == 400
    assert "publisher" in resp.get_json()["error"]


def test_optional_fields_default_to_null(client):
    resp = client.post("/books", json={"title": "Minimal", "author": "Anon"})
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["year"] is None
    assert body["isbn"] is None
