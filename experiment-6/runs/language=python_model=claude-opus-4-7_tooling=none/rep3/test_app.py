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
    os.unlink(db_path)


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_create_book(client):
    resp = client.post(
        "/books",
        json={
            "title": "The Hobbit",
            "author": "J.R.R. Tolkien",
            "year": 1937,
            "isbn": "9780547928227",
        },
    )
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["id"] is not None
    assert data["title"] == "The Hobbit"
    assert data["author"] == "J.R.R. Tolkien"
    assert data["year"] == 1937
    assert data["isbn"] == "9780547928227"


def test_create_book_missing_required_fields(client):
    resp = client.post("/books", json={"year": 2020})
    assert resp.status_code == 400
    body = resp.get_json()
    assert "details" in body
    assert any("title" in d for d in body["details"])
    assert any("author" in d for d in body["details"])


def test_create_book_no_json_body(client):
    resp = client.post("/books", data="not json", content_type="text/plain")
    assert resp.status_code == 400


def test_list_books_empty(client):
    resp = client.get("/books")
    assert resp.status_code == 200
    assert resp.get_json() == []


def test_list_books_filter_by_author(client):
    client.post("/books", json={"title": "A", "author": "Alice"})
    client.post("/books", json={"title": "B", "author": "Bob"})
    client.post("/books", json={"title": "C", "author": "Alice"})

    resp = client.get("/books?author=Alice")
    assert resp.status_code == 200
    books = resp.get_json()
    assert len(books) == 2
    assert {b["title"] for b in books} == {"A", "C"}


def test_get_book_by_id(client):
    create = client.post(
        "/books", json={"title": "1984", "author": "Orwell", "year": 1949}
    )
    book_id = create.get_json()["id"]
    resp = client.get(f"/books/{book_id}")
    assert resp.status_code == 200
    assert resp.get_json()["title"] == "1984"


def test_get_book_not_found(client):
    resp = client.get("/books/9999")
    assert resp.status_code == 404


def test_update_book(client):
    create = client.post(
        "/books", json={"title": "Old Title", "author": "Author"}
    )
    book_id = create.get_json()["id"]
    resp = client.put(
        f"/books/{book_id}", json={"title": "New Title", "year": 2024}
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["title"] == "New Title"
    assert data["author"] == "Author"
    assert data["year"] == 2024


def test_update_book_not_found(client):
    resp = client.put("/books/9999", json={"title": "x", "author": "y"})
    assert resp.status_code == 404


def test_delete_book(client):
    create = client.post(
        "/books", json={"title": "Gone", "author": "Wind"}
    )
    book_id = create.get_json()["id"]
    resp = client.delete(f"/books/{book_id}")
    assert resp.status_code == 204
    follow = client.get(f"/books/{book_id}")
    assert follow.status_code == 404


def test_delete_book_not_found(client):
    resp = client.delete("/books/9999")
    assert resp.status_code == 404
