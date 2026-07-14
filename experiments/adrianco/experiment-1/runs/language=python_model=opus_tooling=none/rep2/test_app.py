import os
import tempfile

import pytest
from fastapi.testclient import TestClient

from app import create_app


@pytest.fixture
def client():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    app = create_app(db_path=path)
    with TestClient(app) as c:
        yield c
    os.unlink(path)


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_create_and_get_book(client):
    r = client.post(
        "/books",
        json={"title": "Dune", "author": "Herbert", "year": 1965, "isbn": "123"},
    )
    assert r.status_code == 201
    book = r.json()
    assert book["title"] == "Dune"
    assert book["id"] > 0

    r2 = client.get(f"/books/{book['id']}")
    assert r2.status_code == 200
    assert r2.json()["author"] == "Herbert"


def test_create_validation(client):
    r = client.post("/books", json={"author": "X"})
    assert r.status_code == 422
    r = client.post("/books", json={"title": "", "author": "X"})
    assert r.status_code == 422


def test_list_and_filter(client):
    client.post("/books", json={"title": "A", "author": "Alice"})
    client.post("/books", json={"title": "B", "author": "Bob"})
    client.post("/books", json={"title": "C", "author": "Alice"})

    r = client.get("/books")
    assert r.status_code == 200
    assert len(r.json()) == 3

    r = client.get("/books?author=Alice")
    assert len(r.json()) == 2
    assert all(b["author"] == "Alice" for b in r.json())


def test_update_and_delete(client):
    r = client.post("/books", json={"title": "Old", "author": "A"})
    book_id = r.json()["id"]

    r = client.put(
        f"/books/{book_id}",
        json={"title": "New", "author": "A", "year": 2020},
    )
    assert r.status_code == 200
    assert r.json()["title"] == "New"
    assert r.json()["year"] == 2020

    r = client.delete(f"/books/{book_id}")
    assert r.status_code == 204

    r = client.get(f"/books/{book_id}")
    assert r.status_code == 404


def test_not_found(client):
    assert client.get("/books/9999").status_code == 404
    assert client.put("/books/9999", json={"title": "T", "author": "A"}).status_code == 404
    assert client.delete("/books/9999").status_code == 404
