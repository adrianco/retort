"""Integration tests for the book collection API."""

import os
import tempfile

import pytest

from app import create_app


@pytest.fixture
def client():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    app = create_app(database=path)
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client
    os.remove(path)


def make_book(client, **overrides):
    payload = {
        "title": "The Pragmatic Programmer",
        "author": "Andrew Hunt",
        "year": 1999,
        "isbn": "978-0201616224",
    }
    payload.update(overrides)
    return client.post("/books", json=payload)


def test_health_check(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_create_book(client):
    resp = make_book(client)
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["id"] > 0
    assert body["title"] == "The Pragmatic Programmer"
    assert body["author"] == "Andrew Hunt"
    assert body["year"] == 1999
    assert body["isbn"] == "978-0201616224"


def test_create_book_missing_required_fields(client):
    resp = client.post("/books", json={"year": 2020})
    assert resp.status_code == 400
    details = resp.get_json()["details"]
    assert any("title" in d for d in details)
    assert any("author" in d for d in details)


def test_create_book_blank_title(client):
    resp = make_book(client, title="   ")
    assert resp.status_code == 400


def test_create_book_invalid_json(client):
    resp = client.post("/books", data="not json", content_type="application/json")
    assert resp.status_code == 400


def test_get_book(client):
    created = make_book(client).get_json()
    resp = client.get(f"/books/{created['id']}")
    assert resp.status_code == 200
    assert resp.get_json()["title"] == "The Pragmatic Programmer"


def test_get_book_not_found(client):
    resp = client.get("/books/9999")
    assert resp.status_code == 404


def test_list_books(client):
    make_book(client, title="Book A", author="Alice")
    make_book(client, title="Book B", author="Bob")
    resp = client.get("/books")
    assert resp.status_code == 200
    assert len(resp.get_json()) == 2


def test_list_books_filter_by_author(client):
    make_book(client, title="Book A", author="Alice")
    make_book(client, title="Book B", author="Bob")
    make_book(client, title="Book C", author="Alice")
    resp = client.get("/books?author=Alice")
    assert resp.status_code == 200
    books = resp.get_json()
    assert len(books) == 2
    assert all(b["author"] == "Alice" for b in books)


def test_update_book(client):
    created = make_book(client).get_json()
    resp = client.put(f"/books/{created['id']}", json={"title": "Updated Title"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["title"] == "Updated Title"
    # Unchanged fields are preserved.
    assert body["author"] == "Andrew Hunt"


def test_update_book_not_found(client):
    resp = client.put("/books/9999", json={"title": "X"})
    assert resp.status_code == 404


def test_update_book_invalid_field(client):
    created = make_book(client).get_json()
    resp = client.put(f"/books/{created['id']}", json={"author": ""})
    assert resp.status_code == 400


def test_delete_book(client):
    created = make_book(client).get_json()
    resp = client.delete(f"/books/{created['id']}")
    assert resp.status_code == 204
    # Confirm it is gone.
    assert client.get(f"/books/{created['id']}").status_code == 404


def test_delete_book_not_found(client):
    resp = client.delete("/books/9999")
    assert resp.status_code == 404
