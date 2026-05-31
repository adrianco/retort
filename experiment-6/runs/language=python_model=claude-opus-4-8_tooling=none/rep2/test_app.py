"""Integration tests for the book collection API."""

import os
import tempfile

import pytest

import app as app_module


@pytest.fixture
def client():
    # Use an isolated temporary database for each test.
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    app_module.DATABASE = path
    application = app_module.create_app()
    application.config["TESTING"] = True
    with application.test_client() as client:
        yield client
    os.remove(path)


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_create_and_get_book(client):
    resp = client.post(
        "/books",
        json={
            "title": "The Go Programming Language",
            "author": "Donovan",
            "year": 2015,
            "isbn": "978-0134190440",
        },
    )
    assert resp.status_code == 201
    created = resp.get_json()
    assert created["id"] > 0
    assert created["title"] == "The Go Programming Language"

    resp = client.get(f"/books/{created['id']}")
    assert resp.status_code == 200
    assert resp.get_json()["author"] == "Donovan"


def test_create_requires_title_and_author(client):
    resp = client.post("/books", json={"title": "No Author"})
    assert resp.status_code == 400
    assert "error" in resp.get_json()

    resp = client.post("/books", json={"author": "No Title"})
    assert resp.status_code == 400

    resp = client.post("/books", json={"title": "   ", "author": "Blank"})
    assert resp.status_code == 400


def test_list_and_author_filter(client):
    client.post("/books", json={"title": "A", "author": "Alice"})
    client.post("/books", json={"title": "B", "author": "Bob"})
    client.post("/books", json={"title": "C", "author": "Alice"})

    resp = client.get("/books")
    assert resp.status_code == 200
    assert len(resp.get_json()) == 3

    resp = client.get("/books?author=Alice")
    assert resp.status_code == 200
    books = resp.get_json()
    assert len(books) == 2
    assert all(b["author"] == "Alice" for b in books)


def test_update_book(client):
    created = client.post(
        "/books", json={"title": "Old", "author": "Author"}
    ).get_json()
    resp = client.put(
        f"/books/{created['id']}", json={"title": "New", "year": 2020}
    )
    assert resp.status_code == 200
    updated = resp.get_json()
    assert updated["title"] == "New"
    assert updated["year"] == 2020
    assert updated["author"] == "Author"


def test_delete_book(client):
    created = client.post(
        "/books", json={"title": "Doomed", "author": "Author"}
    ).get_json()
    resp = client.delete(f"/books/{created['id']}")
    assert resp.status_code == 204

    resp = client.get(f"/books/{created['id']}")
    assert resp.status_code == 404


def test_get_missing_book_returns_404(client):
    assert client.get("/books/9999").status_code == 404
    assert client.put("/books/9999", json={"title": "x"}).status_code == 404
    assert client.delete("/books/9999").status_code == 404
