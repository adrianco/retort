import os
import tempfile
import pytest

from app import create_app


@pytest.fixture
def client():
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    app = create_app(db_path=db_path)
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client
    os.unlink(db_path)


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
    assert body["id"] > 0
    assert body["title"] == "Dune"
    assert body["author"] == "Frank Herbert"
    assert body["year"] == 1965
    assert body["isbn"] == "978-0441172719"

    resp = client.get(f"/books/{body['id']}")
    assert resp.status_code == 200
    assert resp.get_json() == body


def test_create_book_validation_errors(client):
    resp = client.post("/books", json={})
    assert resp.status_code == 400
    errors = resp.get_json()["errors"]
    assert "title is required" in errors
    assert "author is required" in errors

    resp = client.post("/books", json={"title": "  ", "author": "A"})
    assert resp.status_code == 400
    assert "title must be a non-empty string" in resp.get_json()["errors"]

    resp = client.post("/books", data="not json", content_type="application/json")
    assert resp.status_code == 400


def test_list_books_and_author_filter(client):
    client.post("/books", json={"title": "A", "author": "Alice"})
    client.post("/books", json={"title": "B", "author": "Bob"})
    client.post("/books", json={"title": "C", "author": "Alice"})

    resp = client.get("/books")
    assert resp.status_code == 200
    assert len(resp.get_json()) == 3

    resp = client.get("/books?author=Alice")
    assert resp.status_code == 200
    body = resp.get_json()
    assert len(body) == 2
    assert {b["title"] for b in body} == {"A", "C"}

    resp = client.get("/books?author=Nobody")
    assert resp.status_code == 200
    assert resp.get_json() == []


def test_update_book(client):
    created = client.post("/books", json={"title": "Old", "author": "Author"}).get_json()
    resp = client.put(
        f"/books/{created['id']}",
        json={"title": "New", "author": "Author", "year": 2020, "isbn": "123"},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["title"] == "New"
    assert body["year"] == 2020
    assert body["isbn"] == "123"

    resp = client.put("/books/99999", json={"title": "x", "author": "y"})
    assert resp.status_code == 404

    resp = client.put(f"/books/{created['id']}", json={"author": "Only"})
    assert resp.status_code == 400


def test_delete_book(client):
    created = client.post("/books", json={"title": "Bye", "author": "A"}).get_json()
    resp = client.delete(f"/books/{created['id']}")
    assert resp.status_code == 204

    resp = client.get(f"/books/{created['id']}")
    assert resp.status_code == 404

    resp = client.delete(f"/books/{created['id']}")
    assert resp.status_code == 404


def test_get_missing_book(client):
    resp = client.get("/books/12345")
    assert resp.status_code == 404
    assert "error" in resp.get_json()
