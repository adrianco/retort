import os
import tempfile

import pytest

from app import create_app


@pytest.fixture
def client():
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    app = create_app(database_path=db_path)
    app.config.update(TESTING=True)
    with app.test_client() as client:
        yield client
    os.unlink(db_path)


def test_health_endpoint(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_create_book_success(client):
    resp = client.post(
        "/books",
        json={"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"},
    )
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["id"] > 0
    assert data["title"] == "Dune"
    assert data["author"] == "Frank Herbert"
    assert data["year"] == 1965
    assert data["isbn"] == "9780441172719"


def test_create_book_validation_errors(client):
    # Missing title
    resp = client.post("/books", json={"author": "Someone"})
    assert resp.status_code == 400
    assert "title" in resp.get_json()["error"]

    # Missing author
    resp = client.post("/books", json={"title": "Something"})
    assert resp.status_code == 400
    assert "author" in resp.get_json()["error"]

    # Empty title
    resp = client.post("/books", json={"title": "   ", "author": "Someone"})
    assert resp.status_code == 400

    # Invalid year type
    resp = client.post(
        "/books", json={"title": "T", "author": "A", "year": "not-a-year"}
    )
    assert resp.status_code == 400

    # No body
    resp = client.post("/books")
    assert resp.status_code == 400


def test_list_books_and_author_filter(client):
    client.post("/books", json={"title": "Dune", "author": "Frank Herbert"})
    client.post("/books", json={"title": "Foundation", "author": "Isaac Asimov"})
    client.post("/books", json={"title": "Dune Messiah", "author": "Frank Herbert"})

    resp = client.get("/books")
    assert resp.status_code == 200
    assert len(resp.get_json()) == 3

    resp = client.get("/books?author=Frank Herbert")
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data) == 2
    assert all(b["author"] == "Frank Herbert" for b in data)

    resp = client.get("/books?author=Nobody")
    assert resp.status_code == 200
    assert resp.get_json() == []


def test_get_single_book(client):
    created = client.post(
        "/books", json={"title": "1984", "author": "Orwell"}
    ).get_json()

    resp = client.get(f"/books/{created['id']}")
    assert resp.status_code == 200
    assert resp.get_json()["title"] == "1984"

    resp = client.get("/books/99999")
    assert resp.status_code == 404


def test_update_book(client):
    created = client.post(
        "/books", json={"title": "Old", "author": "Author", "year": 2000}
    ).get_json()

    resp = client.put(
        f"/books/{created['id']}",
        json={"title": "New Title", "year": 2024},
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["title"] == "New Title"
    assert data["author"] == "Author"  # unchanged
    assert data["year"] == 2024

    # Invalid update — empty title
    resp = client.put(f"/books/{created['id']}", json={"title": ""})
    assert resp.status_code == 400

    # Update non-existent
    resp = client.put("/books/99999", json={"title": "x"})
    assert resp.status_code == 404


def test_delete_book(client):
    created = client.post(
        "/books", json={"title": "Throwaway", "author": "Nobody"}
    ).get_json()

    resp = client.delete(f"/books/{created['id']}")
    assert resp.status_code == 204

    resp = client.get(f"/books/{created['id']}")
    assert resp.status_code == 404

    # Deleting again returns 404
    resp = client.delete(f"/books/{created['id']}")
    assert resp.status_code == 404
