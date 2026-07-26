"""Integration tests for the book collection API."""
import os
import tempfile

import pytest

import app as app_module


@pytest.fixture
def client():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    flask_app = app_module.create_app(database=path)
    flask_app.config["TESTING"] = True
    app_module.init_db(path)
    with flask_app.test_client() as client:
        yield client
    os.remove(path)


def make_book(client, **overrides):
    payload = {
        "title": "The Hobbit",
        "author": "J.R.R. Tolkien",
        "year": 1937,
        "isbn": "978-0261102217",
    }
    payload.update(overrides)
    return client.post("/books", json=payload)


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"


def test_create_book(client):
    resp = make_book(client)
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["id"] > 0
    assert data["title"] == "The Hobbit"
    assert data["author"] == "J.R.R. Tolkien"


def test_create_book_requires_title_and_author(client):
    resp = client.post("/books", json={"title": "No Author"})
    assert resp.status_code == 400
    assert "author" in resp.get_json()["error"]

    resp = client.post("/books", json={"title": "  ", "author": "x"})
    assert resp.status_code == 400


def test_get_book(client):
    book_id = make_book(client).get_json()["id"]
    resp = client.get(f"/books/{book_id}")
    assert resp.status_code == 200
    assert resp.get_json()["title"] == "The Hobbit"


def test_get_missing_book_returns_404(client):
    assert client.get("/books/9999").status_code == 404


def test_list_and_filter_by_author(client):
    make_book(client, title="Book A", author="Alice")
    make_book(client, title="Book B", author="Bob")
    make_book(client, title="Book C", author="Alice")

    resp = client.get("/books")
    assert resp.status_code == 200
    assert len(resp.get_json()) == 3

    resp = client.get("/books?author=Alice")
    titles = {b["title"] for b in resp.get_json()}
    assert titles == {"Book A", "Book C"}


def test_update_book(client):
    book_id = make_book(client).get_json()["id"]
    resp = client.put(f"/books/{book_id}", json={"year": 1954})
    assert resp.status_code == 200
    assert resp.get_json()["year"] == 1954
    assert resp.get_json()["title"] == "The Hobbit"


def test_update_missing_book_returns_404(client):
    assert client.put("/books/9999", json={"title": "x"}).status_code == 404


def test_update_rejects_empty_title(client):
    book_id = make_book(client).get_json()["id"]
    resp = client.put(f"/books/{book_id}", json={"title": ""})
    assert resp.status_code == 400


def test_delete_book(client):
    book_id = make_book(client).get_json()["id"]
    assert client.delete(f"/books/{book_id}").status_code == 204
    assert client.get(f"/books/{book_id}").status_code == 404


def test_delete_missing_book_returns_404(client):
    assert client.delete("/books/9999").status_code == 404
