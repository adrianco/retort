"""Integration tests for the book collection API."""
import os
import tempfile

import pytest

from app import create_app


@pytest.fixture
def client():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    app = create_app({"DATABASE_PATH": path, "TESTING": True})
    with app.test_client() as c:
        yield c
    os.unlink(path)


def _create(client, **fields):
    payload = {"title": "T", "author": "A"}
    payload.update(fields)
    return client.post("/books", json=payload)


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_create_book_returns_201_with_id(client):
    resp = client.post(
        "/books",
        json={
            "title": "The Hobbit",
            "author": "J.R.R. Tolkien",
            "year": 1937,
            "isbn": "978-0-618-00221-3",
        },
    )
    assert resp.status_code == 201
    body = resp.get_json()
    assert isinstance(body["id"], int)
    assert body["title"] == "The Hobbit"
    assert body["author"] == "J.R.R. Tolkien"
    assert body["year"] == 1937
    assert body["isbn"] == "978-0-618-00221-3"


def test_create_book_without_title_fails(client):
    resp = client.post("/books", json={"author": "Someone"})
    assert resp.status_code == 400
    body = resp.get_json()
    assert "title" in body["details"]


def test_create_book_without_author_fails(client):
    resp = client.post("/books", json={"title": "Anonymous"})
    assert resp.status_code == 400
    body = resp.get_json()
    assert "author" in body["details"]


def test_create_book_with_blank_title_fails(client):
    resp = client.post("/books", json={"title": "   ", "author": "A"})
    assert resp.status_code == 400
    assert "title" in resp.get_json()["details"]


def test_create_book_with_non_integer_year_fails(client):
    resp = client.post(
        "/books", json={"title": "T", "author": "A", "year": "yesterday"}
    )
    assert resp.status_code == 400
    assert "year" in resp.get_json()["details"]


def test_create_book_with_no_body_fails(client):
    resp = client.post("/books")
    assert resp.status_code == 400


def test_list_books_empty(client):
    resp = client.get("/books")
    assert resp.status_code == 200
    assert resp.get_json() == []


def test_list_books_returns_all(client):
    _create(client, title="B1", author="Alice")
    _create(client, title="B2", author="Bob")
    resp = client.get("/books")
    assert resp.status_code == 200
    assert len(resp.get_json()) == 2


def test_list_books_filters_by_author(client):
    _create(client, title="B1", author="Alice")
    _create(client, title="B2", author="Bob")
    _create(client, title="B3", author="Alice")
    resp = client.get("/books?author=Alice")
    assert resp.status_code == 200
    body = resp.get_json()
    assert len(body) == 2
    assert {b["title"] for b in body} == {"B1", "B3"}
    assert all(b["author"] == "Alice" for b in body)


def test_list_books_filter_no_matches(client):
    _create(client, title="B1", author="Alice")
    resp = client.get("/books?author=Nobody")
    assert resp.status_code == 200
    assert resp.get_json() == []


def test_get_book_by_id(client):
    created = _create(client, title="Solo").get_json()
    resp = client.get(f"/books/{created['id']}")
    assert resp.status_code == 200
    assert resp.get_json()["title"] == "Solo"


def test_get_book_not_found(client):
    resp = client.get("/books/99999")
    assert resp.status_code == 404
    assert "error" in resp.get_json()


def test_update_book_replaces_fields(client):
    created = _create(client, title="Old", author="Old Author", year=1990).get_json()
    resp = client.put(
        f"/books/{created['id']}",
        json={
            "title": "New",
            "author": "New Author",
            "year": 2020,
            "isbn": "9999",
        },
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["id"] == created["id"]
    assert body["title"] == "New"
    assert body["author"] == "New Author"
    assert body["year"] == 2020
    assert body["isbn"] == "9999"

    # Persistence check
    fetched = client.get(f"/books/{created['id']}").get_json()
    assert fetched == body


def test_update_book_not_found(client):
    resp = client.put("/books/99999", json={"title": "X", "author": "Y"})
    assert resp.status_code == 404


def test_update_book_validates_required_fields(client):
    created = _create(client).get_json()
    resp = client.put(f"/books/{created['id']}", json={"author": "still here"})
    assert resp.status_code == 400
    assert "title" in resp.get_json()["details"]


def test_delete_book(client):
    created = _create(client).get_json()
    resp = client.delete(f"/books/{created['id']}")
    assert resp.status_code == 204
    assert resp.data == b""
    assert client.get(f"/books/{created['id']}").status_code == 404


def test_delete_book_not_found(client):
    resp = client.delete("/books/99999")
    assert resp.status_code == 404


def test_unknown_route_returns_json_404(client):
    resp = client.get("/does-not-exist")
    assert resp.status_code == 404
    assert resp.is_json


def test_method_not_allowed_returns_json_405(client):
    resp = client.patch("/books")
    assert resp.status_code == 405
    assert resp.is_json


def test_full_crud_lifecycle(client):
    # Create
    created = client.post(
        "/books",
        json={"title": "Lifecycle", "author": "Tester", "year": 2024},
    ).get_json()
    book_id = created["id"]

    # Read
    assert client.get(f"/books/{book_id}").status_code == 200

    # Update
    updated = client.put(
        f"/books/{book_id}",
        json={"title": "Lifecycle v2", "author": "Tester", "year": 2025},
    ).get_json()
    assert updated["title"] == "Lifecycle v2"
    assert updated["year"] == 2025

    # Delete
    assert client.delete(f"/books/{book_id}").status_code == 204
    assert client.get(f"/books/{book_id}").status_code == 404
