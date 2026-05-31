import os
import tempfile
import pytest

from app import create_app


@pytest.fixture
def client():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    app = create_app(path)
    app.testing = True
    with app.test_client() as c:
        yield c
    os.unlink(path)


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_create_book_success(client):
    resp = client.post(
        "/books",
        json={"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441172719"},
    )
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["id"] > 0
    assert body["title"] == "Dune"
    assert body["author"] == "Frank Herbert"
    assert body["year"] == 1965
    assert body["isbn"] == "978-0441172719"


def test_create_book_missing_title(client):
    resp = client.post("/books", json={"author": "Someone"})
    assert resp.status_code == 400
    assert "title" in resp.get_json()["error"]


def test_create_book_missing_author(client):
    resp = client.post("/books", json={"title": "Untitled"})
    assert resp.status_code == 400
    assert "author" in resp.get_json()["error"]


def test_list_books_and_filter_by_author(client):
    client.post("/books", json={"title": "A", "author": "Alice"})
    client.post("/books", json={"title": "B", "author": "Bob"})
    client.post("/books", json={"title": "C", "author": "Alice"})

    resp = client.get("/books")
    assert resp.status_code == 200
    assert len(resp.get_json()) == 3

    resp = client.get("/books?author=Alice")
    assert resp.status_code == 200
    books = resp.get_json()
    assert len(books) == 2
    assert all(b["author"] == "Alice" for b in books)


def test_get_book_by_id(client):
    created = client.post("/books", json={"title": "X", "author": "Y"}).get_json()
    resp = client.get(f"/books/{created['id']}")
    assert resp.status_code == 200
    assert resp.get_json()["title"] == "X"


def test_get_book_not_found(client):
    resp = client.get("/books/9999")
    assert resp.status_code == 404


def test_update_book(client):
    created = client.post(
        "/books",
        json={"title": "Old", "author": "Old", "year": 2000},
    ).get_json()
    resp = client.put(
        f"/books/{created['id']}",
        json={"title": "New", "year": 2024},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["title"] == "New"
    assert body["author"] == "Old"
    assert body["year"] == 2024


def test_update_book_not_found(client):
    resp = client.put("/books/9999", json={"title": "x", "author": "y"})
    assert resp.status_code == 404


def test_delete_book(client):
    created = client.post("/books", json={"title": "Bye", "author": "Z"}).get_json()
    resp = client.delete(f"/books/{created['id']}")
    assert resp.status_code == 204

    resp = client.get(f"/books/{created['id']}")
    assert resp.status_code == 404


def test_delete_book_not_found(client):
    resp = client.delete("/books/9999")
    assert resp.status_code == 404
