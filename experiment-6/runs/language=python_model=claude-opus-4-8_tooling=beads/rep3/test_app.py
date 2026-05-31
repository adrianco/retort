"""Integration tests for the book collection API.

Each test runs against a fresh temporary SQLite database so tests are
isolated and order-independent.
"""

import importlib
import os
import tempfile

import pytest


@pytest.fixture
def client():
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)
    os.environ["BOOKS_DB"] = db_path

    # Re-import the module so it picks up the per-test database path.
    import app as app_module

    importlib.reload(app_module)

    test_app = app_module.create_app()
    test_app.config["TESTING"] = True
    with test_app.test_client() as c:
        yield c

    os.remove(db_path)
    os.environ.pop("BOOKS_DB", None)


def make_book(client, **overrides):
    payload = {
        "title": "The Pragmatic Programmer",
        "author": "Andrew Hunt",
        "year": 1999,
        "isbn": "978-0201616224",
    }
    payload.update(overrides)
    return client.post("/books", json=payload)


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_create_book(client):
    resp = make_book(client)
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["id"] > 0
    assert body["title"] == "The Pragmatic Programmer"
    assert body["author"] == "Andrew Hunt"
    assert body["year"] == 1999


def test_create_book_requires_title_and_author(client):
    resp = client.post("/books", json={"author": "Nobody"})
    assert resp.status_code == 400
    assert "title" in resp.get_json()["error"]

    resp = client.post("/books", json={"title": "Untitled"})
    assert resp.status_code == 400
    assert "author" in resp.get_json()["error"]


def test_create_book_rejects_blank_title(client):
    resp = make_book(client, title="   ")
    assert resp.status_code == 400


def test_get_book(client):
    created = make_book(client).get_json()
    resp = client.get(f"/books/{created['id']}")
    assert resp.status_code == 200
    assert resp.get_json()["title"] == created["title"]


def test_get_missing_book_returns_404(client):
    resp = client.get("/books/9999")
    assert resp.status_code == 404


def test_list_books_and_author_filter(client):
    make_book(client, title="Book A", author="Alice")
    make_book(client, title="Book B", author="Bob")
    make_book(client, title="Book C", author="Alice")

    resp = client.get("/books")
    assert resp.status_code == 200
    assert len(resp.get_json()) == 3

    resp = client.get("/books?author=Alice")
    assert resp.status_code == 200
    titles = {b["title"] for b in resp.get_json()}
    assert titles == {"Book A", "Book C"}


def test_update_book(client):
    created = make_book(client).get_json()
    resp = client.put(f"/books/{created['id']}", json={"year": 2019})
    assert resp.status_code == 200
    assert resp.get_json()["year"] == 2019
    # Other fields untouched.
    assert resp.get_json()["title"] == created["title"]


def test_update_missing_book_returns_404(client):
    resp = client.put("/books/9999", json={"title": "Ghost"})
    assert resp.status_code == 404


def test_delete_book(client):
    created = make_book(client).get_json()
    resp = client.delete(f"/books/{created['id']}")
    assert resp.status_code == 204
    assert client.get(f"/books/{created['id']}").status_code == 404


def test_delete_missing_book_returns_404(client):
    resp = client.delete("/books/9999")
    assert resp.status_code == 404
