"""Tests for the Book Collection REST API."""

import pytest

from app import create_app, init_db


@pytest.fixture
def client(tmp_path):
    db_path = str(tmp_path / "test_books.db")
    init_db(db_path)
    app = create_app(db_path=db_path)
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def create_book(client, **overrides):
    payload = {"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}
    payload.update(overrides)
    return client.post("/books", json=payload)


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_create_book_returns_201_and_book(client):
    resp = create_book(client)
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["title"] == "Dune"
    assert body["author"] == "Frank Herbert"
    assert body["year"] == 1965
    assert body["isbn"] == "9780441172719"
    assert isinstance(body["id"], int)


def test_create_book_requires_title(client):
    resp = client.post("/books", json={"author": "Frank Herbert"})
    assert resp.status_code == 400
    assert "title" in resp.get_json()["error"]


def test_create_book_requires_author(client):
    resp = client.post("/books", json={"title": "Dune"})
    assert resp.status_code == 400
    assert "author" in resp.get_json()["error"]


def test_create_book_rejects_empty_title(client):
    resp = client.post("/books", json={"title": "   ", "author": "X"})
    assert resp.status_code == 400


def test_create_book_rejects_invalid_year(client):
    resp = client.post("/books", json={"title": "T", "author": "A", "year": "1965"})
    assert resp.status_code == 400
    assert "year" in resp.get_json()["error"]


def test_create_book_rejects_non_json_body(client):
    resp = client.post("/books", data="not json", content_type="text/plain")
    assert resp.status_code == 400


def test_list_books(client):
    create_book(client)
    create_book(client, title="Neuromancer", author="William Gibson", year=1984)
    resp = client.get("/books")
    assert resp.status_code == 200
    books = resp.get_json()
    assert len(books) == 2
    assert {b["title"] for b in books} == {"Dune", "Neuromancer"}


def test_list_books_author_filter(client):
    create_book(client)
    create_book(client, title="Neuromancer", author="William Gibson", year=1984)
    resp = client.get("/books?author=William%20Gibson")
    assert resp.status_code == 200
    books = resp.get_json()
    assert len(books) == 1
    assert books[0]["title"] == "Neuromancer"

    empty = client.get("/books?author=Nobody")
    assert empty.status_code == 200
    assert empty.get_json() == []


def test_get_book(client):
    book_id = create_book(client).get_json()["id"]
    resp = client.get(f"/books/{book_id}")
    assert resp.status_code == 200
    assert resp.get_json()["title"] == "Dune"


def test_get_book_not_found(client):
    resp = client.get("/books/9999")
    assert resp.status_code == 404
    assert "not found" in resp.get_json()["error"]


def test_update_book(client):
    book_id = create_book(client).get_json()["id"]
    resp = client.put(f"/books/{book_id}", json={"year": 1966, "title": "Dune Messiah"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["year"] == 1966
    assert body["title"] == "Dune Messiah"
    # untouched fields are preserved
    assert body["author"] == "Frank Herbert"
    assert body["isbn"] == "9780441172719"


def test_update_book_validates_fields(client):
    book_id = create_book(client).get_json()["id"]
    resp = client.put(f"/books/{book_id}", json={"author": ""})
    assert resp.status_code == 400


def test_update_book_not_found(client):
    resp = client.put("/books/9999", json={"title": "X"})
    assert resp.status_code == 404


def test_delete_book(client):
    book_id = create_book(client).get_json()["id"]
    resp = client.delete(f"/books/{book_id}")
    assert resp.status_code == 204
    assert client.get(f"/books/{book_id}").status_code == 404


def test_delete_book_not_found(client):
    resp = client.delete("/books/9999")
    assert resp.status_code == 404


def test_create_then_read_persists(client):
    create_book(client)
    assert len(client.get("/books").get_json()) == 1
