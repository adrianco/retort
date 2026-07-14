import os
import tempfile

import pytest

from app import create_app


@pytest.fixture
def client():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    app = create_app(database=path)
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client
    os.unlink(path)


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_create_book_success(client):
    resp = client.post(
        "/books",
        json={"title": "The Hobbit", "author": "Tolkien", "year": 1937, "isbn": "978-0345339683"},
    )
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["id"] > 0
    assert body["title"] == "The Hobbit"
    assert body["author"] == "Tolkien"
    assert body["year"] == 1937
    assert body["isbn"] == "978-0345339683"


def test_create_book_missing_title(client):
    resp = client.post("/books", json={"author": "Someone"})
    assert resp.status_code == 400
    assert "title" in resp.get_json()["error"].lower()


def test_create_book_missing_author(client):
    resp = client.post("/books", json={"title": "Untitled"})
    assert resp.status_code == 400
    assert "author" in resp.get_json()["error"].lower()


def test_create_book_invalid_year(client):
    resp = client.post(
        "/books", json={"title": "X", "author": "Y", "year": "not-an-int"}
    )
    assert resp.status_code == 400


def test_list_books_empty(client):
    resp = client.get("/books")
    assert resp.status_code == 200
    assert resp.get_json() == []


def test_list_books_with_author_filter(client):
    client.post("/books", json={"title": "Book A", "author": "Alice"})
    client.post("/books", json={"title": "Book B", "author": "Bob"})
    client.post("/books", json={"title": "Book C", "author": "Alice"})

    resp = client.get("/books?author=Alice")
    assert resp.status_code == 200
    body = resp.get_json()
    assert len(body) == 2
    assert all(b["author"] == "Alice" for b in body)


def test_get_book_by_id(client):
    created = client.post(
        "/books", json={"title": "Dune", "author": "Herbert"}
    ).get_json()
    resp = client.get(f"/books/{created['id']}")
    assert resp.status_code == 200
    assert resp.get_json()["title"] == "Dune"


def test_get_book_not_found(client):
    resp = client.get("/books/9999")
    assert resp.status_code == 404


def test_update_book(client):
    created = client.post(
        "/books", json={"title": "Old", "author": "Author"}
    ).get_json()
    resp = client.put(
        f"/books/{created['id']}",
        json={"title": "New", "year": 2020},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["title"] == "New"
    assert body["author"] == "Author"
    assert body["year"] == 2020


def test_update_book_not_found(client):
    resp = client.put("/books/9999", json={"title": "x"})
    assert resp.status_code == 404


def test_delete_book(client):
    created = client.post(
        "/books", json={"title": "Gone", "author": "Author"}
    ).get_json()
    resp = client.delete(f"/books/{created['id']}")
    assert resp.status_code == 204

    follow_up = client.get(f"/books/{created['id']}")
    assert follow_up.status_code == 404


def test_delete_book_not_found(client):
    resp = client.delete("/books/9999")
    assert resp.status_code == 404
