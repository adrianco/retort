"""Integration tests for the book collection API.

Each test runs against a temporary, isolated SQLite database so they never
touch the real ``books.db`` file and don't interfere with each other.
"""

import pytest

from app import create_app


@pytest.fixture
def client(tmp_path):
    db_path = tmp_path / "test_books.db"
    app = create_app(db_path=str(db_path))
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_create_book(client):
    resp = client.post(
        "/books",
        json={"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "123"},
    )
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["id"] > 0
    assert body["title"] == "Dune"
    assert body["author"] == "Frank Herbert"
    assert body["year"] == 1965
    assert body["isbn"] == "123"


def test_create_book_requires_title_and_author(client):
    resp = client.post("/books", json={"year": 2000})
    assert resp.status_code == 400
    error = resp.get_json()["error"]
    assert "title is required" in error
    assert "author is required" in error


def test_create_book_rejects_blank_title(client):
    resp = client.post("/books", json={"title": "   ", "author": "Someone"})
    assert resp.status_code == 400
    assert "title is required" in resp.get_json()["error"]


def test_get_book(client):
    created = client.post(
        "/books", json={"title": "1984", "author": "George Orwell"}
    ).get_json()
    resp = client.get(f"/books/{created['id']}")
    assert resp.status_code == 200
    assert resp.get_json()["title"] == "1984"


def test_get_missing_book_returns_404(client):
    resp = client.get("/books/9999")
    assert resp.status_code == 404


def test_list_books_and_author_filter(client):
    client.post("/books", json={"title": "A", "author": "Alice"})
    client.post("/books", json={"title": "B", "author": "Bob"})
    client.post("/books", json={"title": "C", "author": "Alice"})

    all_books = client.get("/books").get_json()
    assert len(all_books) == 3

    alice_books = client.get("/books?author=Alice").get_json()
    assert len(alice_books) == 2
    assert {b["title"] for b in alice_books} == {"A", "C"}


def test_update_book(client):
    created = client.post(
        "/books", json={"title": "Old", "author": "Author"}
    ).get_json()
    resp = client.put(
        f"/books/{created['id']}",
        json={"title": "New Title", "year": 2020},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["title"] == "New Title"
    assert body["author"] == "Author"  # unchanged
    assert body["year"] == 2020


def test_update_missing_book_returns_404(client):
    resp = client.put("/books/9999", json={"title": "X", "author": "Y"})
    assert resp.status_code == 404


def test_update_book_validation(client):
    created = client.post(
        "/books", json={"title": "Keep", "author": "Author"}
    ).get_json()
    resp = client.put(f"/books/{created['id']}", json={"title": ""})
    assert resp.status_code == 400


def test_delete_book(client):
    created = client.post(
        "/books", json={"title": "Temp", "author": "Author"}
    ).get_json()
    resp = client.delete(f"/books/{created['id']}")
    assert resp.status_code == 204
    assert client.get(f"/books/{created['id']}").status_code == 404


def test_delete_missing_book_returns_404(client):
    resp = client.delete("/books/9999")
    assert resp.status_code == 404
