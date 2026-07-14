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
    with app.test_client() as client:
        yield client
    os.unlink(path)


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_create_and_get_book(client):
    resp = client.post(
        "/books",
        json={"title": "Dune", "author": "Herbert", "year": 1965, "isbn": "123"},
    )
    assert resp.status_code == 201
    book = resp.get_json()
    assert book["id"] and book["title"] == "Dune"

    resp = client.get(f"/books/{book['id']}")
    assert resp.status_code == 200
    assert resp.get_json()["author"] == "Herbert"


def test_create_missing_fields(client):
    resp = client.post("/books", json={"title": "No Author"})
    assert resp.status_code == 400


def test_list_and_filter(client):
    client.post("/books", json={"title": "A", "author": "X"})
    client.post("/books", json={"title": "B", "author": "Y"})
    client.post("/books", json={"title": "C", "author": "X"})

    resp = client.get("/books")
    assert resp.status_code == 200
    assert len(resp.get_json()) == 3

    resp = client.get("/books?author=X")
    assert len(resp.get_json()) == 2


def test_update_and_delete(client):
    resp = client.post("/books", json={"title": "Old", "author": "A"})
    book_id = resp.get_json()["id"]

    resp = client.put(f"/books/{book_id}", json={"title": "New"})
    assert resp.status_code == 200
    assert resp.get_json()["title"] == "New"
    assert resp.get_json()["author"] == "A"

    resp = client.delete(f"/books/{book_id}")
    assert resp.status_code == 204

    resp = client.get(f"/books/{book_id}")
    assert resp.status_code == 404


def test_get_missing(client):
    resp = client.get("/books/9999")
    assert resp.status_code == 404
