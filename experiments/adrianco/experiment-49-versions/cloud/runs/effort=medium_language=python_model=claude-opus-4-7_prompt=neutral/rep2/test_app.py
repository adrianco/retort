import os
import tempfile
import pytest
from app import create_app


@pytest.fixture
def client():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    app = create_app(db_path=path)
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client
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
    book = resp.get_json()
    assert book["id"] > 0
    assert book["title"] == "Dune"
    assert book["author"] == "Frank Herbert"

    resp = client.get(f"/books/{book['id']}")
    assert resp.status_code == 200
    assert resp.get_json()["title"] == "Dune"


def test_create_book_validation(client):
    resp = client.post("/books", json={"author": "Somebody"})
    assert resp.status_code == 400
    assert "title" in resp.get_json()["error"]

    resp = client.post("/books", json={"title": "Only Title"})
    assert resp.status_code == 400
    assert "author" in resp.get_json()["error"]

    resp = client.post("/books", json={"title": "  ", "author": "X"})
    assert resp.status_code == 400


def test_list_and_filter_by_author(client):
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


def test_update_book(client):
    resp = client.post("/books", json={"title": "Old", "author": "Author"})
    book_id = resp.get_json()["id"]

    resp = client.put(f"/books/{book_id}", json={"title": "New Title"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["title"] == "New Title"
    assert body["author"] == "Author"

    resp = client.put("/books/99999", json={"title": "x", "author": "y"})
    assert resp.status_code == 404


def test_delete_book(client):
    resp = client.post("/books", json={"title": "T", "author": "A"})
    book_id = resp.get_json()["id"]

    resp = client.delete(f"/books/{book_id}")
    assert resp.status_code == 204

    resp = client.get(f"/books/{book_id}")
    assert resp.status_code == 404

    resp = client.delete(f"/books/{book_id}")
    assert resp.status_code == 404


def test_get_missing_book(client):
    resp = client.get("/books/12345")
    assert resp.status_code == 404
