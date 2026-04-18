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
    r = client.post("/books", json={
        "title": "Dune", "author": "Herbert", "year": 1965, "isbn": "123"
    })
    assert r.status_code == 201
    book = r.get_json()
    assert book["title"] == "Dune"
    book_id = book["id"]

    r = client.get(f"/books/{book_id}")
    assert r.status_code == 200
    assert r.get_json()["author"] == "Herbert"


def test_create_validation(client):
    r = client.post("/books", json={"author": "X"})
    assert r.status_code == 400
    r = client.post("/books", json={"title": "X"})
    assert r.status_code == 400


def test_list_and_filter(client):
    client.post("/books", json={"title": "A", "author": "X"})
    client.post("/books", json={"title": "B", "author": "Y"})
    client.post("/books", json={"title": "C", "author": "X"})

    r = client.get("/books")
    assert r.status_code == 200
    assert len(r.get_json()) == 3

    r = client.get("/books?author=X")
    data = r.get_json()
    assert len(data) == 2
    assert all(b["author"] == "X" for b in data)


def test_update_and_delete(client):
    r = client.post("/books", json={"title": "Old", "author": "Me"})
    book_id = r.get_json()["id"]

    r = client.put(f"/books/{book_id}", json={"title": "New"})
    assert r.status_code == 200
    assert r.get_json()["title"] == "New"
    assert r.get_json()["author"] == "Me"

    r = client.delete(f"/books/{book_id}")
    assert r.status_code == 204

    r = client.get(f"/books/{book_id}")
    assert r.status_code == 404


def test_update_missing(client):
    r = client.put("/books/999", json={"title": "X", "author": "Y"})
    assert r.status_code == 404
