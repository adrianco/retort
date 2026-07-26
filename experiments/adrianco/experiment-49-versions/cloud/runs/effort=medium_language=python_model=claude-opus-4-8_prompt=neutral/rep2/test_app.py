"""Integration tests for the book collection API."""
import os
import tempfile

import pytest

from app import create_app


@pytest.fixture
def client():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    app = create_app(db_path=path, testing=True)
    with app.test_client() as client:
        yield client
    os.remove(path)


def _make_book(client, **overrides):
    payload = {
        "title": "The Go Programming Language",
        "author": "Donovan",
        "year": 2015,
        "isbn": "978-0134190440",
    }
    payload.update(overrides)
    return client.post("/books", json=payload)


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_create_book(client):
    resp = _make_book(client)
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["id"] > 0
    assert data["title"] == "The Go Programming Language"
    assert data["author"] == "Donovan"
    assert data["year"] == 2015


def test_create_book_requires_title_and_author(client):
    resp = client.post("/books", json={"year": 2000})
    assert resp.status_code == 400
    errors = resp.get_json()["errors"]
    assert any("title" in e for e in errors)
    assert any("author" in e for e in errors)


def test_create_book_rejects_empty_title(client):
    resp = client.post("/books", json={"title": "   ", "author": "X"})
    assert resp.status_code == 400


def test_get_book(client):
    created = _make_book(client).get_json()
    resp = client.get(f"/books/{created['id']}")
    assert resp.status_code == 200
    assert resp.get_json()["title"] == created["title"]


def test_get_missing_book_returns_404(client):
    resp = client.get("/books/9999")
    assert resp.status_code == 404
    assert "error" in resp.get_json()


def test_list_books(client):
    _make_book(client, author="Alice")
    _make_book(client, author="Bob")
    resp = client.get("/books")
    assert resp.status_code == 200
    assert len(resp.get_json()) == 2


def test_list_books_author_filter(client):
    _make_book(client, author="Alice")
    _make_book(client, author="Bob")
    _make_book(client, author="Alice")
    resp = client.get("/books?author=Alice")
    assert resp.status_code == 200
    books = resp.get_json()
    assert len(books) == 2
    assert all(b["author"] == "Alice" for b in books)


def test_update_book(client):
    created = _make_book(client).get_json()
    resp = client.put(f"/books/{created['id']}", json={"title": "New Title"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["title"] == "New Title"
    assert data["author"] == created["author"]  # unchanged


def test_update_missing_book_returns_404(client):
    resp = client.put("/books/9999", json={"title": "Nope"})
    assert resp.status_code == 404


def test_update_rejects_empty_required_field(client):
    created = _make_book(client).get_json()
    resp = client.put(f"/books/{created['id']}", json={"title": ""})
    assert resp.status_code == 400


def test_delete_book(client):
    created = _make_book(client).get_json()
    resp = client.delete(f"/books/{created['id']}")
    assert resp.status_code == 204
    assert client.get(f"/books/{created['id']}").status_code == 404


def test_delete_missing_book_returns_404(client):
    resp = client.delete("/books/9999")
    assert resp.status_code == 404
