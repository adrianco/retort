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
        json={"title": "Dune", "author": "Herbert", "year": 1965, "isbn": "978-0"},
    )
    assert resp.status_code == 201
    book = resp.get_json()
    assert book["id"]
    assert book["title"] == "Dune"

    resp = client.get(f"/books/{book['id']}")
    assert resp.status_code == 200
    assert resp.get_json()["author"] == "Herbert"


def test_create_missing_title_returns_400(client):
    resp = client.post("/books", json={"author": "Someone"})
    assert resp.status_code == 400
    assert "title" in resp.get_json()["error"]


def test_create_missing_author_returns_400(client):
    resp = client.post("/books", json={"title": "X"})
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
    book = client.post("/books", json={"title": "Old", "author": "Auth"}).get_json()
    resp = client.put(f"/books/{book['id']}", json={"title": "New"})
    assert resp.status_code == 200
    assert resp.get_json()["title"] == "New"
    assert resp.get_json()["author"] == "Auth"


def test_update_missing_returns_404(client):
    resp = client.put("/books/999", json={"title": "X", "author": "Y"})
    assert resp.status_code == 404


def test_delete_book(client):
    book = client.post("/books", json={"title": "T", "author": "A"}).get_json()
    resp = client.delete(f"/books/{book['id']}")
    assert resp.status_code == 204
    assert client.get(f"/books/{book['id']}").status_code == 404


def test_get_missing_returns_404(client):
    assert client.get("/books/999").status_code == 404
