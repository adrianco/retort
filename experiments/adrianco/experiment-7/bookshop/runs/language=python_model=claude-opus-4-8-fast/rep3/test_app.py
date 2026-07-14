"""Integration tests for the book collection API."""

import os
import tempfile

import pytest

from app import create_app


@pytest.fixture
def client():
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    app = create_app(db_path=db_path)
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client
    os.remove(db_path)


def sample_book(**overrides):
    book = {
        "title": "The Pragmatic Programmer",
        "author": "Andrew Hunt",
        "year": 1999,
        "isbn": "978-0201616224",
    }
    book.update(overrides)
    return book


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_create_book(client):
    resp = client.post("/books", json=sample_book())
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["id"] > 0
    assert data["title"] == "The Pragmatic Programmer"
    assert data["author"] == "Andrew Hunt"
    assert data["year"] == 1999


def test_create_book_requires_title_and_author(client):
    resp = client.post("/books", json={"author": "Someone"})
    assert resp.status_code == 400
    assert "title" in resp.get_json()["error"]

    resp = client.post("/books", json={"title": "A book"})
    assert resp.status_code == 400
    assert "author" in resp.get_json()["error"]

    resp = client.post("/books", json={"title": "  ", "author": "x"})
    assert resp.status_code == 400


def test_get_book(client):
    created = client.post("/books", json=sample_book()).get_json()
    resp = client.get(f"/books/{created['id']}")
    assert resp.status_code == 200
    assert resp.get_json()["title"] == created["title"]


def test_get_missing_book_returns_404(client):
    resp = client.get("/books/99999")
    assert resp.status_code == 404


def test_list_books_and_author_filter(client):
    client.post("/books", json=sample_book(title="Book A", author="Alice"))
    client.post("/books", json=sample_book(title="Book B", author="Bob"))
    client.post("/books", json=sample_book(title="Book C", author="Alice"))

    resp = client.get("/books")
    assert resp.status_code == 200
    assert len(resp.get_json()) == 3

    resp = client.get("/books?author=Alice")
    assert resp.status_code == 200
    titles = {b["title"] for b in resp.get_json()}
    assert titles == {"Book A", "Book C"}


def test_update_book(client):
    created = client.post("/books", json=sample_book()).get_json()
    resp = client.put(
        f"/books/{created['id']}",
        json=sample_book(title="Updated Title", year=2020),
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["title"] == "Updated Title"
    assert data["year"] == 2020


def test_update_missing_book_returns_404(client):
    resp = client.put("/books/99999", json=sample_book())
    assert resp.status_code == 404


def test_delete_book(client):
    created = client.post("/books", json=sample_book()).get_json()
    resp = client.delete(f"/books/{created['id']}")
    assert resp.status_code == 204
    assert client.get(f"/books/{created['id']}").status_code == 404


def test_delete_missing_book_returns_404(client):
    resp = client.delete("/books/99999")
    assert resp.status_code == 404
