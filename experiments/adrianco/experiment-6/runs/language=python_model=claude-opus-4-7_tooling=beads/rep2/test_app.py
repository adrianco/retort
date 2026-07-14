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
    with app.test_client() as c:
        yield c
    os.unlink(path)


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_create_and_get_book(client):
    resp = client.post(
        "/books",
        json={"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441172719"},
    )
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["id"] >= 1
    assert body["title"] == "Dune"
    assert body["author"] == "Frank Herbert"
    assert body["year"] == 1965
    assert body["isbn"] == "978-0441172719"

    book_id = body["id"]
    got = client.get(f"/books/{book_id}")
    assert got.status_code == 200
    assert got.get_json() == body


def test_create_book_validation(client):
    # Missing title
    resp = client.post("/books", json={"author": "Someone"})
    assert resp.status_code == 400
    assert "title" in resp.get_json()["error"]

    # Missing author
    resp = client.post("/books", json={"title": "Untitled"})
    assert resp.status_code == 400
    assert "author" in resp.get_json()["error"]

    # Blank title
    resp = client.post("/books", json={"title": "   ", "author": "X"})
    assert resp.status_code == 400

    # Wrong year type
    resp = client.post(
        "/books", json={"title": "T", "author": "A", "year": "nineteen"}
    )
    assert resp.status_code == 400

    # Not JSON
    resp = client.post("/books", data="not json", content_type="text/plain")
    assert resp.status_code == 400


def test_list_books_and_filter_by_author(client):
    client.post("/books", json={"title": "A", "author": "Alice"})
    client.post("/books", json={"title": "B", "author": "Bob"})
    client.post("/books", json={"title": "C", "author": "Alice"})

    all_resp = client.get("/books")
    assert all_resp.status_code == 200
    assert len(all_resp.get_json()) == 3

    alice_resp = client.get("/books?author=Alice")
    assert alice_resp.status_code == 200
    alice_books = alice_resp.get_json()
    assert len(alice_books) == 2
    assert {b["title"] for b in alice_books} == {"A", "C"}

    none_resp = client.get("/books?author=Nobody")
    assert none_resp.status_code == 200
    assert none_resp.get_json() == []


def test_update_book(client):
    created = client.post(
        "/books", json={"title": "Old Title", "author": "Author", "year": 2000}
    ).get_json()
    book_id = created["id"]

    resp = client.put(f"/books/{book_id}", json={"title": "New Title", "year": 2024})
    assert resp.status_code == 200
    updated = resp.get_json()
    assert updated["title"] == "New Title"
    assert updated["author"] == "Author"
    assert updated["year"] == 2024

    # Updating a missing book is 404
    missing = client.put("/books/9999", json={"title": "X"})
    assert missing.status_code == 404

    # Blank title rejected on update
    bad = client.put(f"/books/{book_id}", json={"title": ""})
    assert bad.status_code == 400


def test_delete_book(client):
    created = client.post(
        "/books", json={"title": "Doomed", "author": "Author"}
    ).get_json()
    book_id = created["id"]

    resp = client.delete(f"/books/{book_id}")
    assert resp.status_code == 204
    assert resp.data == b""

    follow = client.get(f"/books/{book_id}")
    assert follow.status_code == 404

    # Deleting again is 404
    again = client.delete(f"/books/{book_id}")
    assert again.status_code == 404


def test_get_missing_book(client):
    resp = client.get("/books/12345")
    assert resp.status_code == 404
    assert "error" in resp.get_json()
