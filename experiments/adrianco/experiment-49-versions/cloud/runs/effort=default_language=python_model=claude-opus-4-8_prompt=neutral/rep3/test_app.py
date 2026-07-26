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


def _make_book(client, **overrides):
    payload = {"title": "The Hobbit", "author": "J.R.R. Tolkien", "year": 1937, "isbn": "978-0"}
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
    assert book["title"] == "The Hobbit"

    resp = client.get(f"/books/{book['id']}")
    assert resp.status_code == 200
    assert resp.get_json()["author"] == "J.R.R. Tolkien"


def test_create_requires_title_and_author(client):
    resp = client.post("/books", json={"author": "Someone"})
    assert resp.status_code == 400
    assert "title" in resp.get_json()["error"]

    resp = client.post("/books", json={"title": "  "})
    assert resp.status_code == 400


def test_list_and_author_filter(client):
    _make_book(client, title="A", author="Alice")
    _make_book(client, title="B", author="Bob")
    _make_book(client, title="C", author="Alice")

    resp = client.get("/books")
    assert resp.status_code == 200
    assert len(resp.get_json()) == 3

    resp = client.get("/books?author=Alice")
    assert resp.status_code == 200
    titles = sorted(b["title"] for b in resp.get_json())
    assert titles == ["A", "C"]


def test_update_book(client):
    book = _make_book(client).get_json()
    resp = client.put(f"/books/{book['id']}", json={"year": 2000})
    assert resp.status_code == 200
    assert resp.get_json()["year"] == 2000
    # unchanged fields preserved
    assert resp.get_json()["title"] == "The Hobbit"


def test_update_missing_book(client):
    resp = client.put("/books/999", json={"title": "X"})
    assert resp.status_code == 404


def test_delete_book(client):
    book = _make_book(client).get_json()
    resp = client.delete(f"/books/{book['id']}")
    assert resp.status_code == 204

    resp = client.get(f"/books/{book['id']}")
    assert resp.status_code == 404


def test_delete_missing_book(client):
    resp = client.delete("/books/12345")
    assert resp.status_code == 404


def test_get_missing_book(client):
    resp = client.get("/books/777")
    assert resp.status_code == 404
