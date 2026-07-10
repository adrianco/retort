"""Tests for the Book Collection REST API."""
import os
import sys
import json
import tempfile
import sqlite3
import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import app

_original_db = app.DATABASE


@pytest.fixture(autouse=True)
def test_db():
    """Set up a temporary database for each test and clean up after."""
    db_path = tempfile.mktemp(suffix=".db")
    app.DATABASE = db_path

    db = sqlite3.connect(db_path)
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER,
            isbn TEXT
        )
        """
    )
    db.commit()
    db.close()

    app.app.config["TESTING"] = True
    with app.app.test_client() as client:
        yield client

    app.DATABASE = _original_db
    if os.path.exists(db_path):
        os.remove(db_path)


def test_health_check(test_db):
    """Health check returns 200 and a healthy status."""
    resp = test_db.get("/health")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert data["status"] == "healthy"


def test_create_book(test_db):
    """POST /books with valid data returns 201 and the new book."""
    payload = {
        "title": "The Great Gatsby",
        "author": "F. Scott Fitzgerald",
        "year": 1925,
        "isbn": "978-0743273565",
    }
    resp = test_db.post("/books", json=payload)
    assert resp.status_code == 201
    data = json.loads(resp.data)
    assert data["title"] == "The Great Gatsby"
    assert data["author"] == "F. Scott Fitzgerald"
    assert data["year"] == 1925
    assert data["isbn"] == "978-0743273565"
    assert "id" in data


def test_create_book_missing_title(test_db):
    """POST /books without title returns 400."""
    payload = {"author": "J.K. Rowling", "year": 1997}
    resp = test_db.post("/books", json=payload)
    assert resp.status_code == 400
    data = json.loads(resp.data)
    assert "error" in data


def test_create_book_missing_author(test_db):
    """POST /books without author returns 400."""
    payload = {"title": "Harry Potter", "year": 1997}
    resp = test_db.post("/books", json=payload)
    assert resp.status_code == 400
    data = json.loads(resp.data)
    assert "error" in data


def test_create_book_partial_data(test_db):
    """POST /books with only required fields succeeds."""
    payload = {"title": "Simple Book", "author": "Author Name"}
    resp = test_db.post("/books", json=payload)
    assert resp.status_code == 201
    data = json.loads(resp.data)
    assert data["title"] == "Simple Book"
    assert data["author"] == "Author Name"
    assert data["year"] is None
    assert data["isbn"] is None


def test_create_book_empty_title(test_db):
    """POST /books with empty title returns 400."""
    payload = {"title": "", "author": "Author Name"}
    resp = test_db.post("/books", json=payload)
    assert resp.status_code == 400


def test_create_book_empty_author(test_db):
    """POST /books with empty author returns 400."""
    payload = {"title": "Book Title", "author": ""}
    resp = test_db.post("/books", json=payload)
    assert resp.status_code == 400


def test_create_book_invalid_json(test_db):
    """POST /books with invalid JSON returns 400."""
    resp = test_db.post(
        "/books", data="invalid json", content_type="application/json"
    )
    assert resp.status_code == 400


def test_list_books_empty(test_db):
    """GET /books with no books returns an empty list."""
    resp = test_db.get("/books")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert data == []


def test_list_books(test_db):
    """GET /books returns all created books."""
    book1 = {
        "title": "The Great Gatsby",
        "author": "F. Scott Fitzgerald",
        "year": 1925,
    }
    book2 = {
        "title": "To Kill a Mockingbird",
        "author": "Harper Lee",
        "year": 1960,
    }
    test_db.post("/books", json=book1)
    test_db.post("/books", json=book2)

    resp = test_db.get("/books")
    assert resp.status_code == 200
    books = json.loads(resp.data)
    assert len(books) == 2


def test_list_books_filter_by_author(test_db):
    """GET /books?author= returns only matching books."""
    book1 = {
        "title": "The Great Gatsby",
        "author": "F. Scott Fitzgerald",
        "year": 1925,
    }
    book2 = {
        "title": "To Kill a Mockingbird",
        "author": "Harper Lee",
        "year": 1960,
    }
    test_db.post("/books", json=book1)
    test_db.post("/books", json=book2)

    resp = test_db.get("/books?author=Fitzgerald")
    assert resp.status_code == 200
    books = json.loads(resp.data)
    assert len(books) == 1
    assert books[0]["author"] == "F. Scott Fitzgerald"


def test_get_book_by_id(test_db):
    """GET /books/{id} returns the book."""
    book = {
        "title": "The Great Gatsby",
        "author": "F. Scott Fitzgerald",
        "year": 1925,
    }
    resp = test_db.post("/books", json=book)
    book_id = json.loads(resp.data)["id"]

    resp = test_db.get(f"/books/{book_id}")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert data["title"] == "The Great Gatsby"
    assert data["id"] == book_id


def test_get_book_not_found(test_db):
    """GET /books/999 returns 404 when the book does not exist."""
    resp = test_db.get("/books/999")
    assert resp.status_code == 404
    data = json.loads(resp.data)
    assert "error" in data


def test_update_book(test_db):
    """PUT /books/{id} updates the book and preserves unchanged fields."""
    book = {
        "title": "The Great Gatsby",
        "author": "F. Scott Fitzgerald",
        "year": 1925,
    }
    resp = test_db.post("/books", json=book)
    book_id = json.loads(resp.data)["id"]

    update = {"title": "The Great Gatsby (Updated)"}
    resp = test_db.put(f"/books/{book_id}", json=update)
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert data["title"] == "The Great Gatsby (Updated)"
    assert data["author"] == "F. Scott Fitzgerald"


def test_update_book_not_found(test_db):
    """PUT /books/999 returns 404 for a non-existent book."""
    resp = test_db.put("/books/999", json={"title": "X"})
    assert resp.status_code == 404


def test_delete_book(test_db):
    """DELETE /books/{id} removes the book and verifies removal."""
    book = {
        "title": "The Great Gatsby",
        "author": "F. Scott Fitzgerald",
        "year": 1925,
    }
    resp = test_db.post("/books", json=book)
    book_id = json.loads(resp.data)["id"]

    resp = test_db.delete(f"/books/{book_id}")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert "message" in data

    resp = test_db.get(f"/books/{book_id}")
    assert resp.status_code == 404


def test_delete_book_not_found(test_db):
    """DELETE /books/999 returns 404 for a non-existent book."""
    resp = test_db.delete("/books/999")
    assert resp.status_code == 404
