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


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_create_book_success(client):
    resp = client.post(
        "/books",
        json={"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"},
    )
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["id"] > 0
    assert body["title"] == "Dune"
    assert body["author"] == "Frank Herbert"
    assert body["year"] == 1965
    assert body["isbn"] == "9780441172719"


def test_create_book_missing_title(client):
    resp = client.post("/books", json={"author": "Someone"})
    assert resp.status_code == 400
    assert "title" in resp.get_json()["error"]


def test_create_book_missing_author(client):
    resp = client.post("/books", json={"title": "Only Title"})
    assert resp.status_code == 400
    assert "author" in resp.get_json()["error"]


def test_create_book_empty_body(client):
    resp = client.post("/books", json=None)
    assert resp.status_code == 400


def test_list_books_empty(client):
    resp = client.get("/books")
    assert resp.status_code == 200
    assert resp.get_json() == []


def test_list_books_filter_by_author(client):
    client.post("/books", json={"title": "Dune", "author": "Frank Herbert"})
    client.post("/books", json={"title": "Foundation", "author": "Isaac Asimov"})
    client.post("/books", json={"title": "Dune Messiah", "author": "Frank Herbert"})

    resp = client.get("/books?author=Frank Herbert")
    assert resp.status_code == 200
    body = resp.get_json()
    assert len(body) == 2
    assert {b["title"] for b in body} == {"Dune", "Dune Messiah"}

    resp = client.get("/books")
    assert len(resp.get_json()) == 3


def test_get_book_by_id(client):
    created = client.post(
        "/books", json={"title": "1984", "author": "George Orwell", "year": 1949}
    ).get_json()

    resp = client.get(f"/books/{created['id']}")
    assert resp.status_code == 200
    assert resp.get_json()["title"] == "1984"


def test_get_book_not_found(client):
    resp = client.get("/books/9999")
    assert resp.status_code == 404


def test_update_book(client):
    created = client.post(
        "/books", json={"title": "Old Title", "author": "Author"}
    ).get_json()

    resp = client.put(
        f"/books/{created['id']}", json={"title": "New Title", "year": 2020}
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["title"] == "New Title"
    assert body["author"] == "Author"
    assert body["year"] == 2020


def test_update_book_not_found(client):
    resp = client.put("/books/9999", json={"title": "X"})
    assert resp.status_code == 404


def test_update_book_invalid_field(client):
    created = client.post(
        "/books", json={"title": "T", "author": "A"}
    ).get_json()
    resp = client.put(f"/books/{created['id']}", json={"title": "   "})
    assert resp.status_code == 400


def test_delete_book(client):
    created = client.post(
        "/books", json={"title": "T", "author": "A"}
    ).get_json()

    resp = client.delete(f"/books/{created['id']}")
    assert resp.status_code == 204

    resp = client.get(f"/books/{created['id']}")
    assert resp.status_code == 404


def test_delete_book_not_found(client):
    resp = client.delete("/books/9999")
    assert resp.status_code == 404


def test_full_crud_flow(client):
    resp = client.post("/books", json={"title": "A", "author": "B", "year": 2001})
    assert resp.status_code == 201
    book_id = resp.get_json()["id"]

    resp = client.get(f"/books/{book_id}")
    assert resp.status_code == 200

    resp = client.put(f"/books/{book_id}", json={"year": 2002})
    assert resp.get_json()["year"] == 2002

    resp = client.delete(f"/books/{book_id}")
    assert resp.status_code == 204

    resp = client.get("/books")
    assert resp.get_json() == []
