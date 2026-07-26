"""Integration tests for the book collection API."""
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
    with app.test_client() as c:
        yield c
    os.remove(path)


def make_book(client, title="The Hobbit", author="Tolkien", year=1937, isbn="123"):
    return client.post(
        "/books",
        json={"title": title, "author": author, "year": year, "isbn": isbn},
    )


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"


def test_create_and_get_book(client):
    resp = make_book(client)
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["id"] > 0
    assert data["title"] == "The Hobbit"

    resp = client.get(f"/books/{data['id']}")
    assert resp.status_code == 200
    assert resp.get_json()["author"] == "Tolkien"


def test_create_missing_required_fields(client):
    resp = client.post("/books", json={"title": "No Author"})
    assert resp.status_code == 400
    assert "author" in resp.get_json()["error"]

    resp = client.post("/books", json={"author": "No Title"})
    assert resp.status_code == 400
    assert "title" in resp.get_json()["error"]


def test_list_and_author_filter(client):
    make_book(client, title="Book A", author="Alice")
    make_book(client, title="Book B", author="Bob")
    make_book(client, title="Book C", author="Alice")

    resp = client.get("/books")
    assert resp.status_code == 200
    assert len(resp.get_json()) == 3

    resp = client.get("/books?author=Alice")
    assert resp.status_code == 200
    books = resp.get_json()
    assert len(books) == 2
    assert all(b["author"] == "Alice" for b in books)


def test_update_book(client):
    book_id = make_book(client).get_json()["id"]
    resp = client.put(f"/books/{book_id}", json={"year": 1951})
    assert resp.status_code == 200
    assert resp.get_json()["year"] == 1951
    assert resp.get_json()["title"] == "The Hobbit"


def test_delete_book(client):
    book_id = make_book(client).get_json()["id"]
    resp = client.delete(f"/books/{book_id}")
    assert resp.status_code == 204
    assert client.get(f"/books/{book_id}").status_code == 404


def test_get_missing_book(client):
    assert client.get("/books/999").status_code == 404


def test_invalid_year_type(client):
    resp = client.post(
        "/books",
        json={"title": "T", "author": "A", "year": "not-a-year"},
    )
    assert resp.status_code == 400
