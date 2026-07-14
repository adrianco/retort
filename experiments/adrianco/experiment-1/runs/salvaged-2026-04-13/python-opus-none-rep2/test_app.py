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
    r = client.get("/health")
    assert r.status_code == 200
    assert r.get_json() == {"status": "ok"}


def test_create_and_get_book(client):
    r = client.post("/books", json={"title": "Dune", "author": "Herbert", "year": 1965, "isbn": "123"})
    assert r.status_code == 201
    book = r.get_json()
    assert book["title"] == "Dune"
    assert book["id"]

    r2 = client.get(f"/books/{book['id']}")
    assert r2.status_code == 200
    assert r2.get_json()["author"] == "Herbert"


def test_create_validation(client):
    r = client.post("/books", json={"title": "No Author"})
    assert r.status_code == 400


def test_list_with_author_filter(client):
    client.post("/books", json={"title": "A", "author": "Alice"})
    client.post("/books", json={"title": "B", "author": "Bob"})
    client.post("/books", json={"title": "C", "author": "Alice"})
    r = client.get("/books?author=Alice")
    assert r.status_code == 200
    books = r.get_json()
    assert len(books) == 2
    assert all(b["author"] == "Alice" for b in books)


def test_update_and_delete(client):
    r = client.post("/books", json={"title": "X", "author": "Y"})
    bid = r.get_json()["id"]

    r2 = client.put(f"/books/{bid}", json={"title": "X2"})
    assert r2.status_code == 200
    assert r2.get_json()["title"] == "X2"
    assert r2.get_json()["author"] == "Y"

    r3 = client.delete(f"/books/{bid}")
    assert r3.status_code == 204

    r4 = client.get(f"/books/{bid}")
    assert r4.status_code == 404


def test_get_missing_book(client):
    r = client.get("/books/9999")
    assert r.status_code == 404
