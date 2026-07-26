"""Integration tests for the book collection API."""

import pytest

from app import create_app


@pytest.fixture
def client(tmp_path):
    app = create_app(db_path=str(tmp_path / "test_books.db"))
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def make_book(client, **overrides):
    payload = {
        "title": "The Pragmatic Programmer",
        "author": "Andrew Hunt",
        "year": 1999,
        "isbn": "978-0201616224",
    }
    payload.update(overrides)
    return client.post("/books", json=payload)


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_create_book(client):
    resp = make_book(client)
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["id"] == 1
    assert body["title"] == "The Pragmatic Programmer"
    assert body["author"] == "Andrew Hunt"
    assert body["year"] == 1999
    assert body["isbn"] == "978-0201616224"


def test_create_book_optional_fields_default_to_null(client):
    resp = client.post("/books", json={"title": "Sundiver", "author": "David Brin"})
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["year"] is None
    assert body["isbn"] is None


def test_create_book_validation_errors(client):
    resp = client.post("/books", json={"year": 2020})
    assert resp.status_code == 400
    errors = resp.get_json()["errors"]
    assert any("title" in e for e in errors)
    assert any("author" in e for e in errors)

    resp = client.post("/books", json={"title": "  ", "author": "A"})
    assert resp.status_code == 400

    resp = client.post("/books", json={"title": "T", "author": "A", "year": "not-a-year"})
    assert resp.status_code == 400

    resp = client.post("/books", data="not json", content_type="application/json")
    assert resp.status_code == 400


def test_list_books_and_author_filter(client):
    make_book(client, title="Book One", author="Alice")
    make_book(client, title="Book Two", author="Bob")
    make_book(client, title="Book Three", author="Alice")

    resp = client.get("/books")
    assert resp.status_code == 200
    assert len(resp.get_json()) == 3

    resp = client.get("/books?author=Alice")
    assert resp.status_code == 200
    books = resp.get_json()
    assert len(books) == 2
    assert all(b["author"] == "Alice" for b in books)

    resp = client.get("/books?author=Nobody")
    assert resp.get_json() == []


def test_get_single_book(client):
    created = make_book(client).get_json()
    resp = client.get(f"/books/{created['id']}")
    assert resp.status_code == 200
    assert resp.get_json() == created


def test_get_missing_book_returns_404(client):
    resp = client.get("/books/999")
    assert resp.status_code == 404
    assert resp.get_json()["error"] == "book not found"


def test_update_book(client):
    created = make_book(client).get_json()
    resp = client.put(
        f"/books/{created['id']}",
        json={"title": "Updated Title", "year": 2005},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["title"] == "Updated Title"
    assert body["year"] == 2005
    assert body["author"] == created["author"]

    resp = client.put(f"/books/{created['id']}", json={"title": ""})
    assert resp.status_code == 400

    resp = client.put("/books/999", json={"title": "X"})
    assert resp.status_code == 404


def test_delete_book(client):
    created = make_book(client).get_json()
    resp = client.delete(f"/books/{created['id']}")
    assert resp.status_code == 204

    assert client.get(f"/books/{created['id']}").status_code == 404
    assert client.delete(f"/books/{created['id']}").status_code == 404
