import os
import tempfile

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.environ["BOOKS_DB"] = path
    import importlib
    import app as app_module
    importlib.reload(app_module)
    app_module.init_db()
    with TestClient(app_module.app) as c:
        yield c
    os.remove(path)


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_create_and_get_book(client):
    r = client.post("/books", json={"title": "Dune", "author": "Herbert", "year": 1965, "isbn": "123"})
    assert r.status_code == 201
    book = r.json()
    assert book["id"] >= 1
    assert book["title"] == "Dune"

    r = client.get(f"/books/{book['id']}")
    assert r.status_code == 200
    assert r.json()["author"] == "Herbert"


def test_create_validation_missing_title(client):
    r = client.post("/books", json={"author": "X"})
    assert r.status_code == 422


def test_create_validation_empty_title(client):
    r = client.post("/books", json={"title": "", "author": "X"})
    assert r.status_code == 422


def test_list_and_filter_by_author(client):
    client.post("/books", json={"title": "A", "author": "Alice"})
    client.post("/books", json={"title": "B", "author": "Bob"})
    client.post("/books", json={"title": "C", "author": "Alice"})

    r = client.get("/books")
    assert r.status_code == 200
    assert len(r.json()) == 3

    r = client.get("/books", params={"author": "Alice"})
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 2
    assert all(b["author"] == "Alice" for b in data)


def test_update_book(client):
    r = client.post("/books", json={"title": "Old", "author": "Me"})
    bid = r.json()["id"]
    r = client.put(f"/books/{bid}", json={"title": "New"})
    assert r.status_code == 200
    assert r.json()["title"] == "New"
    assert r.json()["author"] == "Me"


def test_delete_book(client):
    r = client.post("/books", json={"title": "X", "author": "Y"})
    bid = r.json()["id"]
    r = client.delete(f"/books/{bid}")
    assert r.status_code == 204
    r = client.get(f"/books/{bid}")
    assert r.status_code == 404


def test_get_missing_book(client):
    r = client.get("/books/99999")
    assert r.status_code == 404
