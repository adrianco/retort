"""Integration tests for the book collection API."""
import os
import tempfile

import pytest

import app as app_module


@pytest.fixture
def client():
    # Use a fresh temporary database for each test.
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    app_module.DATABASE = path
    app_module.init_db()

    flask_app = app_module.create_app()
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as client:
        yield client

    os.remove(path)


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_create_book(client):
    resp = client.post(
        "/books",
        json={"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593"},
    )
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["id"] > 0
    assert data["title"] == "Dune"
    assert data["author"] == "Frank Herbert"
    assert data["year"] == 1965


def test_create_book_requires_title_and_author(client):
    resp = client.post("/books", json={"title": "No Author"})
    assert resp.status_code == 400
    assert "author" in resp.get_json()["error"]

    resp = client.post("/books", json={"author": "No Title"})
    assert resp.status_code == 400
    assert "title" in resp.get_json()["error"]

    resp = client.post("/books", json={"title": "   ", "author": "x"})
    assert resp.status_code == 400


def test_get_book(client):
    created = client.post("/books", json={"title": "1984", "author": "Orwell"}).get_json()
    resp = client.get(f"/books/{created['id']}")
    assert resp.status_code == 200
    assert resp.get_json()["title"] == "1984"

    assert client.get("/books/99999").status_code == 404


def test_list_books_and_author_filter(client):
    client.post("/books", json={"title": "A", "author": "Alice"})
    client.post("/books", json={"title": "B", "author": "Bob"})
    client.post("/books", json={"title": "C", "author": "Alice"})

    resp = client.get("/books")
    assert resp.status_code == 200
    assert len(resp.get_json()) == 3

    resp = client.get("/books?author=Alice")
    assert resp.status_code == 200
    titles = {b["title"] for b in resp.get_json()}
    assert titles == {"A", "C"}


def test_update_book(client):
    created = client.post("/books", json={"title": "Old", "author": "Author"}).get_json()
    resp = client.put(f"/books/{created['id']}", json={"title": "New", "year": 2020})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["title"] == "New"
    assert data["author"] == "Author"
    assert data["year"] == 2020

    assert client.put("/books/99999", json={"title": "x"}).status_code == 404


def test_delete_book(client):
    created = client.post("/books", json={"title": "Doomed", "author": "Author"}).get_json()
    resp = client.delete(f"/books/{created['id']}")
    assert resp.status_code == 204
    assert client.get(f"/books/{created['id']}").status_code == 404
    assert client.delete("/books/99999").status_code == 404
