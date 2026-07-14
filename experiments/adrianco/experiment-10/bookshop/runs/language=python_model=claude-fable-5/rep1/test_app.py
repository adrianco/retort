"""Integration tests for the book collection API."""

import pytest

from app import create_app


@pytest.fixture
def client(tmp_path):
    app = create_app(db_path=str(tmp_path / "test.db"))
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def make_book(client, **overrides):
    payload = {
        "title": "Release It!",
        "author": "Michael Nygard",
        "year": 2018,
        "isbn": "978-1680502398",
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
    assert body["id"] == 1
    assert body["title"] == "Release It!"
    assert body["author"] == "Michael Nygard"
    assert body["year"] == 2018
    assert body["isbn"] == "978-1680502398"


def test_create_book_requires_title_and_author(client):
    resp = client.post("/books", json={"year": 2020})
    assert resp.status_code == 400
    errors = resp.get_json()["errors"]
    assert any("title" in e for e in errors)
    assert any("author" in e for e in errors)

    resp = client.post("/books", json={"title": "  ", "author": "Someone"})
    assert resp.status_code == 400


def test_create_book_rejects_non_json_body(client):
    resp = client.post("/books", data="not json", content_type="text/plain")
    assert resp.status_code == 400


def test_list_books_and_author_filter(client):
    make_book(client)
    make_book(client, title="Sun Performance", author="Adrian Cockcroft", year=1998)

    resp = client.get("/books")
    assert resp.status_code == 200
    assert len(resp.get_json()) == 2

    resp = client.get("/books?author=Adrian Cockcroft")
    books = resp.get_json()
    assert len(books) == 1
    assert books[0]["title"] == "Sun Performance"

    resp = client.get("/books?author=Nobody")
    assert resp.get_json() == []


def test_get_single_book(client):
    book_id = make_book(client).get_json()["id"]
    resp = client.get(f"/books/{book_id}")
    assert resp.status_code == 200
    assert resp.get_json()["id"] == book_id

    resp = client.get("/books/999")
    assert resp.status_code == 404


def test_update_book(client):
    book_id = make_book(client).get_json()["id"]

    resp = client.put(f"/books/{book_id}", json={"title": "Release It! 2nd Ed", "year": 2018})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["title"] == "Release It! 2nd Ed"
    assert body["author"] == "Michael Nygard"  # unchanged

    resp = client.put(f"/books/{book_id}", json={"title": ""})
    assert resp.status_code == 400

    resp = client.put("/books/999", json={"title": "Ghost"})
    assert resp.status_code == 404


def test_delete_book(client):
    book_id = make_book(client).get_json()["id"]

    resp = client.delete(f"/books/{book_id}")
    assert resp.status_code == 204
    assert client.get(f"/books/{book_id}").status_code == 404

    resp = client.delete(f"/books/{book_id}")
    assert resp.status_code == 404
