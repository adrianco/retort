"""Integration tests for the book collection REST API."""
from __future__ import annotations

import os
import tempfile

import pytest

from app import create_app


@pytest.fixture
def client():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    app = create_app(db_path=path)
    app.config.update(TESTING=True)
    with app.test_client() as c:
        yield c
    os.unlink(path)


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_create_and_get_book(client):
    resp = client.post(
        "/books",
        json={"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441172719"},
    )
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["id"] > 0
    assert body["title"] == "Dune"
    assert body["author"] == "Frank Herbert"
    assert body["year"] == 1965
    assert body["isbn"] == "978-0441172719"

    got = client.get(f"/books/{body['id']}")
    assert got.status_code == 200
    assert got.get_json() == body


def test_create_missing_required_fields(client):
    resp = client.post("/books", json={"title": "Only Title"})
    assert resp.status_code == 400
    assert "author" in resp.get_json()["error"]

    resp = client.post("/books", json={"author": "Only Author"})
    assert resp.status_code == 400
    assert "title" in resp.get_json()["error"]

    resp = client.post("/books", json={"title": "  ", "author": "Someone"})
    assert resp.status_code == 400


def test_list_and_filter_by_author(client):
    client.post("/books", json={"title": "Dune", "author": "Frank Herbert"})
    client.post("/books", json={"title": "Foundation", "author": "Isaac Asimov"})
    client.post("/books", json={"title": "Dune Messiah", "author": "Frank Herbert"})

    resp = client.get("/books")
    assert resp.status_code == 200
    assert len(resp.get_json()) == 3

    resp = client.get("/books?author=Frank Herbert")
    assert resp.status_code == 200
    titles = sorted(b["title"] for b in resp.get_json())
    assert titles == ["Dune", "Dune Messiah"]

    resp = client.get("/books?author=Nobody")
    assert resp.status_code == 200
    assert resp.get_json() == []


def test_update_book(client):
    created = client.post(
        "/books", json={"title": "1984", "author": "George Orwell", "year": 1948}
    ).get_json()

    resp = client.put(f"/books/{created['id']}", json={"year": 1949})
    assert resp.status_code == 200
    assert resp.get_json()["year"] == 1949
    assert resp.get_json()["title"] == "1984"

    resp = client.put("/books/9999", json={"title": "Nothing"})
    assert resp.status_code == 404


def test_delete_book(client):
    created = client.post(
        "/books", json={"title": "Neuromancer", "author": "William Gibson"}
    ).get_json()

    resp = client.delete(f"/books/{created['id']}")
    assert resp.status_code == 204

    resp = client.get(f"/books/{created['id']}")
    assert resp.status_code == 404

    resp = client.delete(f"/books/{created['id']}")
    assert resp.status_code == 404


def test_get_missing_book_returns_404(client):
    resp = client.get("/books/424242")
    assert resp.status_code == 404
    assert "error" in resp.get_json()


def test_rejects_unknown_fields(client):
    resp = client.post(
        "/books",
        json={"title": "T", "author": "A", "wat": "no"},
    )
    assert resp.status_code == 400
    assert "wat" in resp.get_json()["error"]
