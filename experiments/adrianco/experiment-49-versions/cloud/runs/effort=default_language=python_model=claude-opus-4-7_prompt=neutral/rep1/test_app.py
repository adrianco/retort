import os
import tempfile

import pytest

import app as app_module


@pytest.fixture
def client():
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)
    application = app_module.create_app(database_path=db_path)
    application.config["TESTING"] = True
    with application.test_client() as client:
        yield client
    os.unlink(db_path)


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
            "isbn": "978-0345339683",
        },
    )
    assert response.status_code == 201
    body = response.get_json()
    assert body["id"] > 0
    assert body["title"] == "The Hobbit"
    assert body["author"] == "J.R.R. Tolkien"
    assert body["year"] == 1937
    assert body["isbn"] == "978-0345339683"

    book_id = body["id"]
    get_response = client.get(f"/books/{book_id}")
    assert get_response.status_code == 200
    assert get_response.get_json() == body


def test_create_book_validation_missing_fields(client):
    response = client.post("/books", json={"year": 2020})
    assert response.status_code == 400
    body = response.get_json()
    assert body["error"] == "Validation failed"
    assert any("title" in msg for msg in body["details"])
    assert any("author" in msg for msg in body["details"])


def test_create_book_rejects_empty_title(client):
    response = client.post(
        "/books", json={"title": "   ", "author": "Someone"}
    )
    assert response.status_code == 400
    assert response.get_json()["error"] == "Validation failed"


def test_list_books_and_filter_by_author(client):
    client.post("/books", json={"title": "Book A", "author": "Alice"})
    client.post("/books", json={"title": "Book B", "author": "Bob"})
    client.post("/books", json={"title": "Book C", "author": "Alice"})

    all_books = client.get("/books")
    assert all_books.status_code == 200
    assert len(all_books.get_json()) == 3

    alice_books = client.get("/books?author=Alice")
    assert alice_books.status_code == 200
    body = alice_books.get_json()
    assert len(body) == 2
    assert all(b["author"] == "Alice" for b in body)

    no_match = client.get("/books?author=Nobody")
    assert no_match.status_code == 200
    assert no_match.get_json() == []


def test_update_book(client):
    created = client.post(
        "/books", json={"title": "Old Title", "author": "Author"}
    ).get_json()
    book_id = created["id"]

    response = client.put(
        f"/books/{book_id}",
        json={"title": "New Title", "year": 2024},
    )
    assert response.status_code == 200
    body = response.get_json()
    assert body["title"] == "New Title"
    assert body["author"] == "Author"
    assert body["year"] == 2024


def test_update_book_not_found(client):
    response = client.put("/books/999", json={"title": "x", "author": "y"})
    assert response.status_code == 404


def test_update_book_invalid_payload(client):
    created = client.post(
        "/books", json={"title": "T", "author": "A"}
    ).get_json()
    response = client.put(
        f"/books/{created['id']}", json={"title": ""}
    )
    assert response.status_code == 400


def test_delete_book(client):
    created = client.post(
        "/books", json={"title": "To Delete", "author": "Author"}
    ).get_json()
    book_id = created["id"]

    delete_response = client.delete(f"/books/{book_id}")
    assert delete_response.status_code == 204

    get_response = client.get(f"/books/{book_id}")
    assert get_response.status_code == 404


def test_delete_book_not_found(client):
    response = client.delete("/books/999")
    assert response.status_code == 404


def test_get_book_not_found(client):
    response = client.get("/books/999")
    assert response.status_code == 404
    assert response.get_json()["error"] == "Book not found"


def test_create_book_requires_json_body(client):
    response = client.post("/books", data="not json", content_type="text/plain")
    assert response.status_code == 400
