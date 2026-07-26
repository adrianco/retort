"""Integration tests for the book collection API.

Each test runs against a fresh in-memory-style database backed by a temporary
file, so tests are isolated and repeatable.
"""

import pytest

from app import create_app


@pytest.fixture
def client(tmp_path):
    db_path = tmp_path / "test_books.db"
    app = create_app(database=str(db_path))
    app.config.update(TESTING=True)
    with app.test_client() as client:
        yield client


def _make_book(client, **overrides):
    payload = {
        "title": "The Go Programming Language",
        "author": "Alan Donovan",
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
    body = resp.get_json()
    assert body["id"] > 0
    assert body["title"] == "The Go Programming Language"
    assert body["author"] == "Alan Donovan"
    assert body["year"] == 2015


def test_create_book_requires_title_and_author(client):
    resp = client.post("/books", json={"author": "Nobody"})
    assert resp.status_code == 400
    assert "title" in resp.get_json()["error"]

    resp = client.post("/books", json={"title": "Untitled"})
    assert resp.status_code == 400
    assert "author" in resp.get_json()["error"]

    resp = client.post("/books", json={"title": "  ", "author": "x"})
    assert resp.status_code == 400


def test_get_book_and_not_found(client):
    created = _make_book(client).get_json()
    resp = client.get(f"/books/{created['id']}")
    assert resp.status_code == 200
    assert resp.get_json()["id"] == created["id"]

    resp = client.get("/books/99999")
    assert resp.status_code == 404


def test_list_and_filter_by_author(client):
    _make_book(client, title="Book A", author="Alice")
    _make_book(client, title="Book B", author="Bob")
    _make_book(client, title="Book C", author="Alice")

    resp = client.get("/books")
    assert resp.status_code == 200
    assert len(resp.get_json()) == 3

    resp = client.get("/books?author=Alice")
    assert resp.status_code == 200
    titles = {b["title"] for b in resp.get_json()}
    assert titles == {"Book A", "Book C"}


def test_update_book(client):
    created = _make_book(client).get_json()
    resp = client.put(f"/books/{created['id']}", json={"year": 2016})
    assert resp.status_code == 200
    assert resp.get_json()["year"] == 2016
    # unchanged fields are preserved
    assert resp.get_json()["title"] == created["title"]

    resp = client.put("/books/99999", json={"title": "x", "author": "y"})
    assert resp.status_code == 404


def test_update_book_rejects_invalid(client):
    created = _make_book(client).get_json()
    resp = client.put(f"/books/{created['id']}", json={"title": ""})
    assert resp.status_code == 400


def test_delete_book(client):
    created = _make_book(client).get_json()
    resp = client.delete(f"/books/{created['id']}")
    assert resp.status_code == 204

    resp = client.get(f"/books/{created['id']}")
    assert resp.status_code == 404

    resp = client.delete(f"/books/{created['id']}")
    assert resp.status_code == 404


def test_invalid_json_body(client):
    resp = client.post(
        "/books", data="not json", content_type="application/json"
    )
    assert resp.status_code == 400
