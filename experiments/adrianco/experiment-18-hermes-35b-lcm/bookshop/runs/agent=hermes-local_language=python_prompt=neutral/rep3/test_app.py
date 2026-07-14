"""Tests for the Book Collection REST API."""

import os
import pytest
import json
import tempfile

from app import app, db, Book


def make_client():
    """Create a test client with a temporary database."""
    tmpfile = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmpfile.close()
    db_path = f"file:{tmpfile.name}?mode=memory&cache=shared"
    
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{tmpfile.name}"
    app.config["TESTING"] = True

    with app.app_context():
        db.drop_all()
        db.create_all()

    with app.test_client() as test_client:
        yield test_client

    os.unlink(tmpfile.name)


@pytest.fixture
def client():
    """Create a test client with a fresh temporary database."""
    tmpfile = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmpfile.close()
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{tmpfile.name}"
    app.config["TESTING"] = True
    with app.app_context():
        db.drop_all()
        db.create_all()
    try:
        with app.test_client() as test_client:
            yield test_client
    finally:
        with app.app_context():
            db.drop_all()
        os.unlink(tmpfile.name)


@pytest.fixture()
def sample_book(client):
    """Create and return a sample book."""
    book_data = {
        "title": "The Great Gatsby",
        "author": "F. Scott Fitzgerald",
        "year": 1925,
        "isbn": "978-0743273565",
    }
    resp = client.post(
        "/books",
        data=json.dumps(book_data),
        content_type="application/json",
    )
    assert resp.status_code == 201
    return resp.get_json()


def test_health_check(client):
    """GET /health returns 200 and status healthy."""
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "healthy"


def test_create_book(client):
    """POST /books creates a new book and returns 201."""
    book_data = {
        "title": "1984",
        "author": "George Orwell",
        "year": 1949,
        "isbn": "978-0451524935",
    }
    resp = client.post(
        "/books",
        data=json.dumps(book_data),
        content_type="application/json",
    )
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["title"] == "1984"
    assert data["author"] == "George Orwell"
    assert data["year"] == 1949
    assert data["isbn"] == "978-0451524935"
    assert "id" in data


def test_create_book_missing_title(client):
    """POST /books without title returns 400."""
    book_data = {
        "author": "George Orwell",
        "year": 1949,
    }
    resp = client.post(
        "/books",
        data=json.dumps(book_data),
        content_type="application/json",
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert "Title is required" in data["error"]


def test_create_book_missing_author(client):
    """POST /books without author returns 400."""
    book_data = {
        "title": "1984",
        "year": 1949,
    }
    resp = client.post(
        "/books",
        data=json.dumps(book_data),
        content_type="application/json",
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert "Author is required" in data["error"]


def test_list_books(client, sample_book):
    """GET /books returns all books."""
    # Create a second book
    book_data = {
        "title": "Animal Farm",
        "author": "George Orwell",
        "year": 1945,
    }
    client.post(
        "/books",
        data=json.dumps(book_data),
        content_type="application/json",
    )

    resp = client.get("/books")
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data) == 2


def test_list_books_filter_by_author(client, sample_book):
    """GET /books?author=Orwell returns only George Orwell books."""
    # Create books by different authors
    book_data = {
        "title": "Brave New World",
        "author": "Aldous Huxley",
    }
    client.post(
        "/books",
        data=json.dumps(book_data),
        content_type="application/json",
    )
    book_data2 = {
        "title": "Animal Farm",
        "author": "George Orwell",
    }
    client.post(
        "/books",
        data=json.dumps(book_data2),
        content_type="application/json",
    )

    resp = client.get("/books?author=Orwell")
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data) == 1
    assert data[0]["author"] == "George Orwell"


def test_get_book_by_id(client, sample_book):
    """GET /books/<id> returns the book."""
    book_id = sample_book["id"]
    resp = client.get(f"/books/{book_id}")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["id"] == book_id
    assert data["title"] == "The Great Gatsby"


def test_get_book_not_found(client):
    """GET /books/999 returns 404 for non-existent book."""
    resp = client.get("/books/999")
    assert resp.status_code == 404


def test_update_book(client, sample_book):
    """PUT /books/<id> updates the book."""
    book_id = sample_book["id"]
    update_data = {"title": "The Great Gatsby (Updated)", "year": 1926}

    resp = client.put(
        f"/books/{book_id}",
        data=json.dumps(update_data),
        content_type="application/json",
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["title"] == "The Great Gatsby (Updated)"
    assert data["year"] == 1926
    # Author should be unchanged
    assert data["author"] == "F. Scott Fitzgerald"


def test_update_nonexistent_book(client):
    """PUT /books/999 returns 404."""
    resp = client.put(
        "/books/999",
        data=json.dumps({"title": "None"}),
        content_type="application/json",
    )
    assert resp.status_code == 404


def test_delete_book(client, sample_book):
    """DELETE /books/<id> removes the book."""
    book_id = sample_book["id"]
    resp = client.delete(f"/books/{book_id}")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["message"] == "Book deleted"

    # Verify it's gone
    resp = client.get(f"/books/{book_id}")
    assert resp.status_code == 404


def test_delete_nonexistent_book(client):
    """DELETE /books/999 returns 404."""
    resp = client.delete("/books/999")
    assert resp.status_code == 404
