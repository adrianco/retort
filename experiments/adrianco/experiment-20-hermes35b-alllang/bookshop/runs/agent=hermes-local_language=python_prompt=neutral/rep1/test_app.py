"""Integration tests for Book Collection REST API."""

import json
import os
import tempfile

import pytest

import app


@pytest.fixture
def client():
    """Create a test client with a temporary SQLite database."""
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)

    test_app, test_db, Book = app.create_app(test_db_path=db_path)
    test_app.config["TESTING"] = True

    with test_app.app_context():
        test_db.create_all()

    with test_app.test_client() as test_client:
        yield test_client

    os.unlink(db_path)


def _json_headers():
    return {"Content-Type": "application/json"}


# -----------------------------------------------------------------------
# Health endpoint
# -----------------------------------------------------------------------

def test_health(client):
    """GET /health returns 200 with ok status."""
    resp = client.get("/health")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert data["status"] == "ok"


# -----------------------------------------------------------------------
# Create book (POST /books)
# -----------------------------------------------------------------------

def test_create_book_success(client):
    """POST /books creates a book and returns 201."""
    payload = {
        "title": "The Great Gatsby",
        "author": "F. Scott Fitzgerald",
        "year": 1925,
        "isbn": "978-0743273565",
    }
    resp = client.post(
        "/books", data=json.dumps(payload), headers=_json_headers()
    )
    assert resp.status_code == 201
    data = json.loads(resp.data)
    assert data["title"] == "The Great Gatsby"
    assert data["author"] == "F. Scott Fitzgerald"
    assert data["year"] == 1925
    assert data["isbn"] == "978-0743273565"
    assert data["id"] is not None


def test_create_book_missing_title(client):
    """POST /books without title returns 400."""
    payload = {"author": "Someone"}
    resp = client.post(
        "/books", data=json.dumps(payload), headers=_json_headers()
    )
    assert resp.status_code == 400
    data = json.loads(resp.data)
    assert "error" in data


def test_create_book_missing_author(client):
    """POST /books without author returns 400."""
    payload = {"title": "Some Book"}
    resp = client.post(
        "/books", data=json.dumps(payload), headers=_json_headers()
    )
    assert resp.status_code == 400


def test_create_book_no_body(client):
    """POST /books with empty body returns 400."""
    resp = client.post(
        "/books", data=json.dumps({}), headers=_json_headers()
    )
    assert resp.status_code == 400


# -----------------------------------------------------------------------
# List books (GET /books)
# -----------------------------------------------------------------------

def _create_books(client):
    """Helper: create several books for listing tests."""
    books = [
        {"title": "Book A", "author": "Author One", "year": 2000, "isbn": "111"},
        {"title": "Book B", "author": "Author Two", "year": 2010, "isbn": "222"},
        {"title": "Book C", "author": "Author One", "year": 2020, "isbn": "333"},
    ]
    for b in books:
        client.post("/books", data=json.dumps(b), headers=_json_headers())


def test_list_books(client):
    """GET /books returns all books."""
    _create_books(client)
    resp = client.get("/books")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert isinstance(data, list)
    assert len(data) == 3


def test_list_books_filter_by_author(client):
    """GET /books?author= returns filtered books."""
    _create_books(client)
    resp = client.get("/books?author=Author One")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert len(data) == 2
    for b in data:
        assert "Author One" in b["author"]


# -----------------------------------------------------------------------
# Get single book (GET /books/<id>)
# -----------------------------------------------------------------------

def test_get_book_success(client):
    """GET /books/<id> returns a book."""
    payload = {"title": "1984", "author": "George Orwell", "year": 1949}
    resp = client.post("/books", data=json.dumps(payload), headers=_json_headers())
    book_id = json.loads(resp.data)["id"]

    resp = client.get(f"/books/{book_id}")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert data["title"] == "1984"


def test_get_book_not_found(client):
    """GET /books/999 returns 404."""
    resp = client.get("/books/999")
    assert resp.status_code == 404
    data = json.loads(resp.data)
    assert "error" in data


# -----------------------------------------------------------------------
# Update book (PUT /books/<id>)
# -----------------------------------------------------------------------

def test_update_book_success(client):
    """PUT /books/<id> updates a book and returns 200."""
    payload = {"title": "Old Title", "author": "Old Author", "year": 1900}
    resp = client.post("/books", data=json.dumps(payload), headers=_json_headers())
    book_id = json.loads(resp.data)["id"]

    update = {"title": "New Title", "year": 2000}
    resp = client.put(
        f"/books/{book_id}", data=json.dumps(update), headers=_json_headers()
    )
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert data["title"] == "New Title"
    assert data["year"] == 2000
    assert data["author"] == "Old Author"


def test_update_book_not_found(client):
    """PUT /books/999 returns 404."""
    resp = client.put(
        "/books/999", data=json.dumps({}), headers=_json_headers()
    )
    assert resp.status_code == 404


def test_update_book_blank_title(client):
    """PUT /books/<id> with empty title returns 400."""
    payload = {"title": "Valid", "author": "Author", "year": 2000}
    resp = client.post("/books", data=json.dumps(payload), headers=_json_headers())
    book_id = json.loads(resp.data)["id"]

    update = {"title": "", "author": "Author"}
    resp = client.put(
        f"/books/{book_id}", data=json.dumps(update), headers=_json_headers()
    )
    assert resp.status_code == 400


# -----------------------------------------------------------------------
# Delete book (DELETE /books/<id>)
# -----------------------------------------------------------------------

def test_delete_book_success(client):
    """DELETE /books/<id> removes the book and returns 200."""
    payload = {"title": "To Be Deleted", "author": "Author", "year": 2020}
    resp = client.post("/books", data=json.dumps(payload), headers=_json_headers())
    book_id = json.loads(resp.data)["id"]

    resp = client.delete(f"/books/{book_id}")
    assert resp.status_code == 200

    resp = client.get(f"/books/{book_id}")
    assert resp.status_code == 404


def test_delete_book_not_found(client):
    """DELETE /books/999 returns 404."""
    resp = client.delete("/books/999")
    assert resp.status_code == 404
