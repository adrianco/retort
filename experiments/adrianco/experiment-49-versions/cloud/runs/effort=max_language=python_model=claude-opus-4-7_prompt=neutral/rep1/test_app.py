from __future__ import annotations

import os
import tempfile

import pytest

from app import create_app


@pytest.fixture
def client():
    fd, path = tempfile.mkstemp(suffix=".db", prefix="books-test-")
    os.close(fd)
    os.unlink(path)  # let the app recreate it
    app = create_app(database=path)
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c
    if os.path.exists(path):
        os.unlink(path)


def test_health_returns_ok(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_create_and_get_book(client):
    resp = client.post(
        "/books",
        json={
            "title": "Dune",
            "author": "Frank Herbert",
            "year": 1965,
            "isbn": "978-0441172719",
        },
    )
    assert resp.status_code == 201
    book = resp.get_json()
    assert book["id"] > 0
    assert book["title"] == "Dune"
    assert book["author"] == "Frank Herbert"
    assert book["year"] == 1965
    assert book["isbn"] == "978-0441172719"
    assert resp.headers["Location"] == f"/books/{book['id']}"

    r2 = client.get(f"/books/{book['id']}")
    assert r2.status_code == 200
    assert r2.get_json() == book


def test_create_book_missing_title_returns_400(client):
    r = client.post("/books", json={"author": "Someone"})
    assert r.status_code == 400
    body = r.get_json()
    assert "title" in body["error"]


def test_create_book_missing_author_returns_400(client):
    r = client.post("/books", json={"title": "Untitled"})
    assert r.status_code == 400
    body = r.get_json()
    assert "author" in body["error"]


def test_create_book_blank_title_returns_400(client):
    r = client.post("/books", json={"title": "   ", "author": "Someone"})
    assert r.status_code == 400


def test_create_book_bad_year_type_returns_400(client):
    r = client.post(
        "/books",
        json={"title": "T", "author": "A", "year": "nineteen-sixty-five"},
    )
    assert r.status_code == 400


def test_create_book_no_body_returns_400(client):
    r = client.post("/books")
    assert r.status_code == 400


def test_list_books_empty(client):
    r = client.get("/books")
    assert r.status_code == 200
    assert r.get_json() == []


def test_list_books_and_author_filter(client):
    payloads = [
        {"title": "A", "author": "Alice"},
        {"title": "B", "author": "Alice", "year": 2000},
        {"title": "C", "author": "Bob"},
    ]
    for p in payloads:
        assert client.post("/books", json=p).status_code == 201

    r_all = client.get("/books")
    assert r_all.status_code == 200
    assert len(r_all.get_json()) == 3

    r_alice = client.get("/books?author=Alice")
    assert r_alice.status_code == 200
    titles = sorted(b["title"] for b in r_alice.get_json())
    assert titles == ["A", "B"]

    r_none = client.get("/books?author=Nobody")
    assert r_none.status_code == 200
    assert r_none.get_json() == []


def test_update_book(client):
    created = client.post(
        "/books", json={"title": "Old", "author": "Author"}
    ).get_json()
    book_id = created["id"]

    r = client.put(
        f"/books/{book_id}",
        json={"title": "New", "author": "Author2", "year": 2020},
    )
    assert r.status_code == 200
    updated = r.get_json()
    assert updated["id"] == book_id
    assert updated["title"] == "New"
    assert updated["author"] == "Author2"
    assert updated["year"] == 2020
    assert updated["isbn"] is None

    fetched = client.get(f"/books/{book_id}").get_json()
    assert fetched == updated


def test_update_nonexistent_book_returns_404(client):
    r = client.put("/books/9999", json={"title": "T", "author": "A"})
    assert r.status_code == 404


def test_update_invalid_payload_returns_400(client):
    created = client.post(
        "/books", json={"title": "T", "author": "A"}
    ).get_json()
    r = client.put(f"/books/{created['id']}", json={"title": "T"})
    assert r.status_code == 400


def test_delete_book(client):
    created = client.post(
        "/books", json={"title": "T", "author": "A"}
    ).get_json()

    r = client.delete(f"/books/{created['id']}")
    assert r.status_code == 204
    assert r.data == b""

    r2 = client.get(f"/books/{created['id']}")
    assert r2.status_code == 404


def test_delete_nonexistent_book_returns_404(client):
    r = client.delete("/books/12345")
    assert r.status_code == 404


def test_get_nonexistent_book_returns_404(client):
    r = client.get("/books/12345")
    assert r.status_code == 404


def test_data_persists_across_requests(client):
    ids = []
    for i in range(3):
        r = client.post(
            "/books",
            json={"title": f"Book {i}", "author": "Same Author", "year": 2000 + i},
        )
        ids.append(r.get_json()["id"])

    assert len(set(ids)) == 3  # unique ids
    listing = client.get("/books").get_json()
    assert [b["id"] for b in listing] == sorted(ids)
