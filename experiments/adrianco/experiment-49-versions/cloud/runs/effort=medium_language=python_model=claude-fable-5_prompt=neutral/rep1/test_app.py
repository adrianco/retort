"""Integration tests for the book collection API."""

import pytest

from app import create_app


@pytest.fixture
def client(tmp_path):
    app = create_app(database=str(tmp_path / "test_books.db"))
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


def test_create_book_validation(client):
    resp = client.post("/books", json={"title": "No Author"})
    assert resp.status_code == 400
    assert any("author" in e for e in resp.get_json()["errors"])

    resp = client.post("/books", json={"title": "  ", "author": "Someone"})
    assert resp.status_code == 400

    resp = client.post("/books", json={"title": "T", "author": "A", "year": "not-a-year"})
    assert resp.status_code == 400

    resp = client.post("/books", data="not json", content_type="application/json")
    assert resp.status_code == 400


def test_list_books_and_author_filter(client):
    make_book(client)
    make_book(client, title="Refactoring", author="Martin Fowler", year=2018)
    make_book(client, title="Patterns of Enterprise Application Architecture",
              author="Martin Fowler", year=2002)

    resp = client.get("/books")
    assert resp.status_code == 200
    assert len(resp.get_json()) == 3

    resp = client.get("/books?author=Martin Fowler")
    books = resp.get_json()
    assert len(books) == 2
    assert all(b["author"] == "Martin Fowler" for b in books)

    resp = client.get("/books?author=Nobody")
    assert resp.get_json() == []


def test_get_book(client):
    book_id = make_book(client).get_json()["id"]
    resp = client.get(f"/books/{book_id}")
    assert resp.status_code == 200
    assert resp.get_json()["title"] == "The Pragmatic Programmer"

    assert client.get("/books/999").status_code == 404


def test_update_book(client):
    book_id = make_book(client).get_json()["id"]

    resp = client.put(f"/books/{book_id}", json={"title": "Updated Title", "year": 2000})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["title"] == "Updated Title"
    assert body["year"] == 2000
    assert body["author"] == "Andrew Hunt"  # unchanged

    resp = client.put(f"/books/{book_id}", json={"title": ""})
    assert resp.status_code == 400

    assert client.put("/books/999", json={"title": "X"}).status_code == 404


def test_delete_book(client):
    book_id = make_book(client).get_json()["id"]
    assert client.delete(f"/books/{book_id}").status_code == 204
    assert client.get(f"/books/{book_id}").status_code == 404
    assert client.delete(f"/books/{book_id}").status_code == 404
