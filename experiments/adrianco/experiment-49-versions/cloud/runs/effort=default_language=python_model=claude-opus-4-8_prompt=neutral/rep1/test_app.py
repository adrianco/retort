"""Integration tests for the book collection API.

Each test runs against a fresh, temporary SQLite database so that tests are
isolated and repeatable.
"""

import os
import tempfile

import pytest

from app import create_app


@pytest.fixture
def client():
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    app = create_app(db_path)
    app.config.update(TESTING=True)
    with app.test_client() as client:
        yield client
    os.remove(db_path)


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


def test_create_book_missing_required_fields(client):
    resp = client.post("/books", json={"title": "No Author"})
    assert resp.status_code == 400
    assert "author" in resp.get_json()["error"]

    resp = client.post("/books", json={"author": "No Title"})
    assert resp.status_code == 400
    assert "title" in resp.get_json()["error"]


def test_create_book_rejects_blank_title(client):
    resp = make_book(client, title="   ")
    assert resp.status_code == 400


def test_get_single_book(client):
    book_id = make_book(client).get_json()["id"]
    resp = client.get(f"/books/{book_id}")
    assert resp.status_code == 200
    assert resp.get_json()["id"] == book_id


def test_get_missing_book_returns_404(client):
    resp = client.get("/books/9999")
    assert resp.status_code == 404


def test_list_books_and_author_filter(client):
    make_book(client, title="A", author="Alice")
    make_book(client, title="B", author="Bob")
    make_book(client, title="C", author="Alice")

    resp = client.get("/books")
    assert resp.status_code == 200
    assert len(resp.get_json()) == 3

    resp = client.get("/books?author=Alice")
    assert resp.status_code == 200
    titles = sorted(b["title"] for b in resp.get_json())
    assert titles == ["A", "C"]


def test_update_book(client):
    book_id = make_book(client).get_json()["id"]
    resp = client.put(f"/books/{book_id}", json={"year": 2019, "title": "New Title"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["year"] == 2019
    assert body["title"] == "New Title"
    # Unspecified fields are preserved.
    assert body["author"] == "Andrew Hunt"


def test_update_missing_book_returns_404(client):
    resp = client.put("/books/9999", json={"title": "X"})
    assert resp.status_code == 404


def test_update_rejects_blank_author(client):
    book_id = make_book(client).get_json()["id"]
    resp = client.put(f"/books/{book_id}", json={"author": ""})
    assert resp.status_code == 400


def test_delete_book(client):
    book_id = make_book(client).get_json()["id"]
    resp = client.delete(f"/books/{book_id}")
    assert resp.status_code == 204
    assert client.get(f"/books/{book_id}").status_code == 404


def test_delete_missing_book_returns_404(client):
    resp = client.delete("/books/9999")
    assert resp.status_code == 404
