import os
import tempfile

import pytest

from app import create_app


@pytest.fixture
def client():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    app = create_app(database_path=path)
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client
    os.unlink(path)


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_create_and_get_book(client):
    response = client.post(
        "/books",
        json={
            "title": "The Hobbit",
            "author": "J.R.R. Tolkien",
            "year": 1937,
            "isbn": "978-0261102217",
        },
    )
    assert response.status_code == 201
    created = response.get_json()
    assert created["id"] > 0
    assert created["title"] == "The Hobbit"
    assert created["author"] == "J.R.R. Tolkien"
    assert created["year"] == 1937
    assert created["isbn"] == "978-0261102217"

    response = client.get(f"/books/{created['id']}")
    assert response.status_code == 200
    assert response.get_json() == created


def test_create_book_missing_title_returns_400(client):
    response = client.post("/books", json={"author": "Someone"})
    assert response.status_code == 400
    assert "title" in response.get_json()["error"]


def test_create_book_missing_author_returns_400(client):
    response = client.post("/books", json={"title": "A Book"})
    assert response.status_code == 400
    assert "author" in response.get_json()["error"]


def test_create_book_empty_title_returns_400(client):
    response = client.post("/books", json={"title": "   ", "author": "X"})
    assert response.status_code == 400


def test_list_books_and_filter_by_author(client):
    client.post("/books", json={"title": "Book A", "author": "Alice"})
    client.post("/books", json={"title": "Book B", "author": "Bob"})
    client.post("/books", json={"title": "Book C", "author": "Alice"})

    response = client.get("/books")
    assert response.status_code == 200
    all_books = response.get_json()
    assert len(all_books) == 3

    response = client.get("/books?author=Alice")
    assert response.status_code == 200
    alice_books = response.get_json()
    assert len(alice_books) == 2
    assert {b["title"] for b in alice_books} == {"Book A", "Book C"}
    assert all(b["author"] == "Alice" for b in alice_books)


def test_update_book(client):
    created = client.post(
        "/books", json={"title": "Old Title", "author": "Author"}
    ).get_json()
    book_id = created["id"]

    response = client.put(
        f"/books/{book_id}",
        json={"title": "New Title", "author": "Author", "year": 2020},
    )
    assert response.status_code == 200
    updated = response.get_json()
    assert updated["id"] == book_id
    assert updated["title"] == "New Title"
    assert updated["year"] == 2020

    response = client.get(f"/books/{book_id}")
    assert response.get_json()["title"] == "New Title"


def test_update_missing_book_returns_404(client):
    response = client.put(
        "/books/9999", json={"title": "X", "author": "Y"}
    )
    assert response.status_code == 404


def test_delete_book(client):
    created = client.post(
        "/books", json={"title": "Doomed", "author": "Nobody"}
    ).get_json()
    book_id = created["id"]

    response = client.delete(f"/books/{book_id}")
    assert response.status_code == 204

    response = client.get(f"/books/{book_id}")
    assert response.status_code == 404


def test_delete_missing_book_returns_404(client):
    response = client.delete("/books/9999")
    assert response.status_code == 404


def test_get_missing_book_returns_404(client):
    response = client.get("/books/9999")
    assert response.status_code == 404
