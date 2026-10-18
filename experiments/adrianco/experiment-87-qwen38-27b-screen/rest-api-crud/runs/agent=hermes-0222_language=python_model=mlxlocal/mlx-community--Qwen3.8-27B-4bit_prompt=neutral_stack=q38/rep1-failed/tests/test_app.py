"""Tests for the book collection REST API.

Covers all endpoints (index, health, create, list + filter, get, update,
delete) including validation and error paths. Run with:

    python -m pytest
"""

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app  # noqa: E402


@pytest.fixture()
def client(tmp_path):
    """A Flask test client backed by a throwaway SQLite database."""
    app = create_app(db_path=str(tmp_path / "books.db"))
    app.testing = True
    with app.test_client() as c:
        yield c


# --------------------------------------------------------------------- #
# Index / health
# --------------------------------------------------------------------- #

def test_index_returns_service_info(client):
    resp = client.get("/")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["service"] == "book-collection-api"
    assert body["health"] == "/health"


def test_health_returns_ok(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


# --------------------------------------------------------------------- #
# POST /books
# --------------------------------------------------------------------- #

def test_create_book_success(client):
    resp = client.post(
        "/books",
        json={
            "title": "The Hobbit",
            "author": "J.R.R. Tolkien",
            "year": 1937,
            "isbn": "978-0-261-10235-9",
        },
    )
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["title"] == "The Hobbit"
    assert body["author"] == "J.R.R. Tolkien"
    assert body["year"] == 1937
    assert body["isbn"] == "978-0-261-10235-9"
    assert isinstance(body["id"], int)


def test_create_book_minimal_fields(client):
    resp = client.post("/books", json={"title": "Dune", "author": "Frank Herbert"})
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["year"] is None
    assert body["isbn"] is None


def test_create_book_missing_title(client):
    resp = client.post("/books", json={"author": "Some Author"})
    assert resp.status_code == 400
    body = resp.get_json()
    assert "title" in body["fields"]


def test_create_book_missing_author(client):
    resp = client.post("/books", json={"title": "Some Title"})
    assert resp.status_code == 400
    body = resp.get_json()
    assert "author" in body["fields"]


def test_create_book_empty_title_rejected(client):
    resp = client.post("/books", json={"title": "   ", "author": "A"})
    assert resp.status_code == 400
    assert "title" in resp.get_json()["fields"]


def test_create_book_invalid_year_rejected(client):
    resp = client.post(
        "/books", json={"title": "T", "author": "A", "year": "not-a-year"}
    )
    assert resp.status_code == 400
    assert "year" in resp.get_json()["fields"]


def test_create_book_invalid_json_rejected(client):
    resp = client.post("/books", data="this is not json", content_type="text/plain")
    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_create_book_non_object_json_rejected(client):
    resp = client.post("/books", json=[1, 2, 3])
    assert resp.status_code == 400


def test_create_book_year_as_numeric_string_accepted(client):
    resp = client.post("/books", json={"title": "T", "author": "A", "year": "1999"})
    assert resp.status_code == 201
    assert resp.get_json()["year"] == 1999


# --------------------------------------------------------------------- #
# GET /books
# --------------------------------------------------------------------- #

def test_list_books_empty(client):
    resp = client.get("/books")
    assert resp.status_code == 200
    assert resp.get_json() == []


def test_list_books_returns_created_books(client):
    client.post("/books", json={"title": "A", "author": "X"})
    client.post("/books", json={"title": "B", "author": "Y"})
    resp = client.get("/books")
    assert resp.status_code == 200
    books = resp.get_json()
    assert [b["title"] for b in books] == ["A", "B"]


def test_list_books_filter_by_author(client):
    client.post("/books", json={"title": "A", "author": "Tolkien"})
    client.post("/books", json={"title": "B", "author": "Le Guin"})
    client.post("/books", json={"title": "C", "author": "Tolkien"})
    resp = client.get("/books?author=Tolkien")
    assert resp.status_code == 200
    books = resp.get_json()
    assert [b["title"] for b in books] == ["A", "C"]


def test_list_books_filter_no_match(client):
    client.post("/books", json={"title": "A", "author": "Tolkien"})
    resp = client.get("/books?author=Nobody")
    assert resp.status_code == 200
    assert resp.get_json() == []


# --------------------------------------------------------------------- #
# GET /books/<id>
# --------------------------------------------------------------------- #

def test_get_book_by_id(client):
    created = client.post(
        "/books", json={"title": "Neuromancer", "author": "William Gibson"}
    ).get_json()
    resp = client.get(f"/books/{created['id']}")
    assert resp.status_code == 200
    assert resp.get_json() == created


def test_get_book_not_found(client):
    resp = client.get("/books/9999")
    assert resp.status_code == 404
    assert "error" in resp.get_json()


def test_get_book_non_integer_id_is_404(client):
    resp = client.get("/books/not-an-id")
    assert resp.status_code == 404


# --------------------------------------------------------------------- #
# PUT /books/<id>
# --------------------------------------------------------------------- #

def test_update_book(client):
    created = client.post(
        "/books", json={"title": "Old Title", "author": "Old Author", "year": 1990}
    ).get_json()
    resp = client.put(
        f"/books/{created['id']}",
        json={"title": "New Title", "author": "New Author", "year": 2000, "isbn": "X"},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["id"] == created["id"]
    assert body["title"] == "New Title"
    assert body["author"] == "New Author"
    assert body["year"] == 2000
    assert body["isbn"] == "X"
    # Persisted: a fresh GET sees the update.
    assert client.get(f"/books/{created['id']}").get_json() == body


def test_update_book_not_found(client):
    resp = client.put(
        "/books/9999", json={"title": "T", "author": "A"}
    )
    assert resp.status_code == 404


def test_update_book_missing_required_fields(client):
    created = client.post("/books", json={"title": "T", "author": "A"}).get_json()
    resp = client.put(f"/books/{created['id']}", json={"title": "Only Title"})
    assert resp.status_code == 400
    assert "author" in resp.get_json()["fields"]


def test_update_book_invalid_json(client):
    created = client.post("/books", json={"title": "T", "author": "A"}).get_json()
    resp = client.put(
        f"/books/{created['id']}", data="nope", content_type="text/plain"
    )
    assert resp.status_code == 400


# --------------------------------------------------------------------- #
# DELETE /books/<id>
# --------------------------------------------------------------------- #

def test_delete_book(client):
    created = client.post("/books", json={"title": "T", "author": "A"}).get_json()
    resp = client.delete(f"/books/{created['id']}")
    assert resp.status_code == 200
    assert client.get(f"/books/{created['id']}").status_code == 404
    assert client.get("/books").get_json() == []


def test_delete_book_not_found(client):
    resp = client.delete("/books/9999")
    assert resp.status_code == 404
    assert "error" in resp.get_json()


# --------------------------------------------------------------------- #
# Cross-cutting
# --------------------------------------------------------------------- #

def test_unknown_route_returns_json_404(client):
    resp = client.get("/nope")
    assert resp.status_code == 404
    assert resp.is_json


def test_wrong_method_returns_json_405(client):
    resp = client.patch("/books")
    assert resp.status_code == 405
    assert resp.is_json
