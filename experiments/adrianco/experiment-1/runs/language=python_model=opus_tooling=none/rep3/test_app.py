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
    r = client.get("/health")
    assert r.status_code == 200
    assert r.get_json() == {"status": "ok"}


def test_create_and_get_book(client):
    r = client.post("/books", json={
        "title": "Dune", "author": "Herbert", "year": 1965, "isbn": "123"
    })
    assert r.status_code == 201
    data = r.get_json()
    assert data["title"] == "Dune"
    book_id = data["id"]

    r = client.get(f"/books/{book_id}")
    assert r.status_code == 200
    assert r.get_json()["author"] == "Herbert"


def test_create_validation(client):
    r = client.post("/books", json={"author": "X"})
    assert r.status_code == 400
    r = client.post("/books", json={"title": "X"})
    assert r.status_code == 400


def test_list_and_filter(client):
    client.post("/books", json={"title": "A", "author": "Alice"})
    client.post("/books", json={"title": "B", "author": "Bob"})
    client.post("/books", json={"title": "C", "author": "Alice"})

    r = client.get("/books")
    assert r.status_code == 200
    assert len(r.get_json()) == 3

    r = client.get("/books?author=Alice")
    assert r.status_code == 200
    rows = r.get_json()
    assert len(rows) == 2
    assert all(b["author"] == "Alice" for b in rows)


def test_update_and_delete(client):
    r = client.post("/books", json={"title": "Old", "author": "A"})
    bid = r.get_json()["id"]

    r = client.put(f"/books/{bid}", json={"title": "New"})
    assert r.status_code == 200
    assert r.get_json()["title"] == "New"
    assert r.get_json()["author"] == "A"

    r = client.delete(f"/books/{bid}")
    assert r.status_code == 204

    r = client.get(f"/books/{bid}")
    assert r.status_code == 404


def test_update_missing(client):
    r = client.put("/books/9999", json={"title": "X", "author": "Y"})
    assert r.status_code == 404
