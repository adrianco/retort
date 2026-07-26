"""Integration tests for the book collection API."""

import pytest

from app import create_app


@pytest.fixture
def client():
    app = create_app(db_path=":memory:")
    app.config["TESTING"] = True
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
    data = resp.get_json()
    assert data["id"] > 0
    assert data["title"] == "The Go Programming Language"
    assert data["author"] == "Alan Donovan"
    assert data["year"] == 2015


def test_create_book_requires_title_and_author(client):
    resp = client.post("/books", json={"year": 2020})
    assert resp.status_code == 400
    assert "title" in resp.get_json()["error"]

    resp = client.post("/books", json={"title": "   ", "author": "X"})
    assert resp.status_code == 400

    resp = client.post("/books", json={"title": "Only Title"})
    assert resp.status_code == 400
    assert "author" in resp.get_json()["error"]


def test_get_single_book(client):
    book_id = _make_book(client).get_json()["id"]
    resp = client.get(f"/books/{book_id}")
    assert resp.status_code == 200
    assert resp.get_json()["id"] == book_id


def test_get_missing_book_returns_404(client):
    resp = client.get("/books/999")
    assert resp.status_code == 404


def test_list_books_and_author_filter(client):
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
    book_id = _make_book(client).get_json()["id"]
    resp = client.put(f"/books/{book_id}", json={"title": "Updated Title"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["title"] == "Updated Title"
    assert data["author"] == "Alan Donovan"  # unchanged


def test_update_missing_book_returns_404(client):
    resp = client.put("/books/999", json={"title": "Nope"})
    assert resp.status_code == 404


def test_update_rejects_empty_title(client):
    book_id = _make_book(client).get_json()["id"]
    resp = client.put(f"/books/{book_id}", json={"title": "  "})
    assert resp.status_code == 400


def test_delete_book(client):
    book_id = _make_book(client).get_json()["id"]
    resp = client.delete(f"/books/{book_id}")
    assert resp.status_code == 204
    assert client.get(f"/books/{book_id}").status_code == 404


def test_delete_missing_book_returns_404(client):
    resp = client.delete("/books/999")
    assert resp.status_code == 404
