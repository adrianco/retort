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
    with app.test_client() as c:
        yield c
    os.unlink(path)


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.get_json() == {"status": "ok"}


def test_create_and_get_book(client):
    r = client.post("/books", json={"title": "Dune", "author": "Herbert", "year": 1965, "isbn": "111"})
    assert r.status_code == 201
    book = r.get_json()
    assert book["id"] > 0
    assert book["title"] == "Dune"

    r2 = client.get(f"/books/{book['id']}")
    assert r2.status_code == 200
    assert r2.get_json()["author"] == "Herbert"


def test_create_validation(client):
    r = client.post("/books", json={"author": "X"})
    assert r.status_code == 400
    r = client.post("/books", json={"title": "T"})
    assert r.status_code == 400
    r = client.post("/books", json={"title": "T", "author": "A", "year": "notanint"})
    assert r.status_code == 400


def test_list_with_author_filter(client):
    client.post("/books", json={"title": "A", "author": "Alice"})
    client.post("/books", json={"title": "B", "author": "Bob"})
    client.post("/books", json={"title": "C", "author": "Alice"})

    r = client.get("/books")
    assert r.status_code == 200
    assert len(r.get_json()) == 3

    r = client.get("/books?author=Alice")
    assert len(r.get_json()) == 2


def test_update_book(client):
    r = client.post("/books", json={"title": "Old", "author": "Auth"})
    bid = r.get_json()["id"]
    r = client.put(f"/books/{bid}", json={"title": "New"})
    assert r.status_code == 200
    assert r.get_json()["title"] == "New"
    assert r.get_json()["author"] == "Auth"

    r = client.put("/books/9999", json={"title": "x"})
    assert r.status_code == 404


def test_delete_book(client):
    r = client.post("/books", json={"title": "T", "author": "A"})
    bid = r.get_json()["id"]
    r = client.delete(f"/books/{bid}")
    assert r.status_code == 204
    r = client.get(f"/books/{bid}")
    assert r.status_code == 404
    r = client.delete(f"/books/{bid}")
    assert r.status_code == 404
