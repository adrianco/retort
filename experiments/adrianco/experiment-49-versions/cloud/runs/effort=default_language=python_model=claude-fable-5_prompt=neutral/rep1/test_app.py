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


def test_create_book_optional_fields(client):
    resp = client.post("/books", json={"title": "Sundiver", "author": "David Brin"})
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["year"] is None
    assert body["isbn"] is None


def test_create_book_validation(client):
    # Missing both required fields
    resp = client.post("/books", json={"year": 2020})
    assert resp.status_code == 400
    errors = resp.get_json()["errors"]
    assert "'title' is required" in errors
    assert "'author' is required" in errors

    # Empty title
    resp = client.post("/books", json={"title": "   ", "author": "Someone"})
    assert resp.status_code == 400

    # Non-integer year
    resp = client.post(
        "/books", json={"title": "T", "author": "A", "year": "nineteen"}
    )
    assert resp.status_code == 400

    # Invalid JSON body
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
    books = resp.get_json()
    assert len(books) == 2
    assert all(b["author"] == "Alice" for b in books)

    resp = client.get("/books?author=Nobody")
    assert resp.get_json() == []


def test_get_book_by_id(client):
    created = make_book(client).get_json()
    resp = client.get(f"/books/{created['id']}")
    assert resp.status_code == 200
    assert resp.get_json() == created

    resp = client.get("/books/999")
    assert resp.status_code == 404
    assert "error" in resp.get_json()


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
    assert body["author"] == created["author"]  # unchanged

    # Update on missing book
    resp = client.put("/books/999", json={"title": "X"})
    assert resp.status_code == 404

    # Invalid update: empty title
    resp = client.put(f"/books/{created['id']}", json={"title": ""})
    assert resp.status_code == 400

    # No fields at all
    resp = client.put(f"/books/{created['id']}", json={})
    assert resp.status_code == 400


def test_delete_book(client):
    created = make_book(client).get_json()
    resp = client.delete(f"/books/{created['id']}")
    assert resp.status_code == 204

    assert client.get(f"/books/{created['id']}").status_code == 404
    assert client.delete(f"/books/{created['id']}").status_code == 404


def test_data_persists_across_requests(client):
    make_book(client, title="Persistent", author="Author")
    resp = client.get("/books")
    titles = [b["title"] for b in resp.get_json()]
    assert "Persistent" in titles
