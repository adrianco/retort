"""Integration tests for the book collection API."""

import os
import tempfile

import pytest

from app import create_app


@pytest.fixture
def client():
    # A fresh temp-file database per test keeps them isolated. An in-memory
    # DB can't be used here because each request opens its own connection.
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    app = create_app(database=path)
    app.config["TESTING"] = True
    try:
        with app.test_client() as client:
            yield client
    finally:
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
    data = resp.get_json()
    assert data["id"] > 0
    assert data["title"] == "The Pragmatic Programmer"
    assert data["author"] == "Andrew Hunt"
    assert data["year"] == 1999


def test_create_book_requires_title_and_author(client):
    resp = client.post("/books", json={"author": "Nobody"})
    assert resp.status_code == 400
    assert "title" in resp.get_json()["error"]

    resp = client.post("/books", json={"title": "Untitled"})
    assert resp.status_code == 400
    assert "author" in resp.get_json()["error"]


def test_create_book_rejects_blank_title(client):
    resp = make_book(client, title="   ")
    assert resp.status_code == 400


def test_get_book(client):
    book_id = make_book(client).get_json()["id"]
    resp = client.get(f"/books/{book_id}")
    assert resp.status_code == 200
    assert resp.get_json()["id"] == book_id


def test_get_missing_book_returns_404(client):
    resp = client.get("/books/9999")
    assert resp.status_code == 404


def test_list_books_and_author_filter(client):
    make_book(client, title="Book A", author="Alice")
    make_book(client, title="Book B", author="Bob")
    make_book(client, title="Book C", author="Alice")

    resp = client.get("/books")
    assert resp.status_code == 200
    assert len(resp.get_json()) == 3

    resp = client.get("/books?author=Alice")
    assert resp.status_code == 200
    titles = {b["title"] for b in resp.get_json()}
    assert titles == {"Book A", "Book C"}


def test_update_book(client):
    book_id = make_book(client).get_json()["id"]
    resp = client.put(f"/books/{book_id}", json={"year": 2019, "title": "New Title"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["year"] == 2019
    assert data["title"] == "New Title"
    assert data["author"] == "Andrew Hunt"  # unchanged


def test_update_missing_book_returns_404(client):
    resp = client.put("/books/9999", json={"title": "x"})
    assert resp.status_code == 404


def test_delete_book(client):
    book_id = make_book(client).get_json()["id"]
    resp = client.delete(f"/books/{book_id}")
    assert resp.status_code == 204
    assert client.get(f"/books/{book_id}").status_code == 404


def test_delete_missing_book_returns_404(client):
    resp = client.delete("/books/9999")
    assert resp.status_code == 404
