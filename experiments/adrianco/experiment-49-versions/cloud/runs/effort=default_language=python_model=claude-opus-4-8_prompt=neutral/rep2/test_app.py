"""Integration tests for the book collection API."""

import os
import tempfile

import pytest

from app import create_app


@pytest.fixture
def client():
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)
    app = create_app(database=db_path)
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client
    os.remove(db_path)


def make_book(client, **overrides):
    payload = {"title": "The Go Programming Language", "author": "Donovan"}
    payload.update(overrides)
    return client.post("/books", json=payload)


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_create_book(client):
    resp = client.post(
        "/books",
        json={"title": "Dune", "author": "Herbert", "year": 1965, "isbn": "12345"},
    )
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["id"] > 0
    assert data["title"] == "Dune"
    assert data["author"] == "Herbert"
    assert data["year"] == 1965
    assert data["isbn"] == "12345"


def test_create_book_missing_required_fields(client):
    resp = client.post("/books", json={"year": 2000})
    assert resp.status_code == 400
    errors = resp.get_json()["errors"]
    assert any("title" in e for e in errors)
    assert any("author" in e for e in errors)


def test_create_book_blank_title(client):
    resp = client.post("/books", json={"title": "   ", "author": "Someone"})
    assert resp.status_code == 400


def test_get_book(client):
    created = make_book(client).get_json()
    resp = client.get(f"/books/{created['id']}")
    assert resp.status_code == 200
    assert resp.get_json()["title"] == "The Go Programming Language"


def test_get_book_not_found(client):
    resp = client.get("/books/9999")
    assert resp.status_code == 404


def test_list_books(client):
    make_book(client, title="A", author="Alice")
    make_book(client, title="B", author="Bob")
    resp = client.get("/books")
    assert resp.status_code == 200
    assert len(resp.get_json()) == 2


def test_list_books_filter_by_author(client):
    make_book(client, title="A", author="Alice")
    make_book(client, title="B", author="Bob")
    make_book(client, title="C", author="Alice")
    resp = client.get("/books?author=Alice")
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data) == 2
    assert all(b["author"] == "Alice" for b in data)


def test_update_book(client):
    created = make_book(client).get_json()
    resp = client.put(
        f"/books/{created['id']}", json={"title": "Updated", "year": 2020}
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["title"] == "Updated"
    assert data["year"] == 2020
    # Author preserved from original.
    assert data["author"] == "Donovan"


def test_update_book_not_found(client):
    resp = client.put("/books/9999", json={"title": "X"})
    assert resp.status_code == 404


def test_update_book_blank_author_rejected(client):
    created = make_book(client).get_json()
    resp = client.put(f"/books/{created['id']}", json={"author": "  "})
    assert resp.status_code == 400


def test_delete_book(client):
    created = make_book(client).get_json()
    resp = client.delete(f"/books/{created['id']}")
    assert resp.status_code == 204
    assert client.get(f"/books/{created['id']}").status_code == 404


def test_delete_book_not_found(client):
    resp = client.delete("/books/9999")
    assert resp.status_code == 404
