"""Tests for the Book Collection REST API."""

import os
import sys
import json
import tempfile
import pytest

# Ensure the app module can be imported
sys.path.insert(0, os.path.dirname(__file__))

import app as app_module


@pytest.fixture
def client():
    """Create a test client with a temporary database."""
    tmpfd, tmpdb = tempfile.mkstemp(suffix=".db")
    os.close(tmpfd)

    original_db = app_module.DATABASE
    app_module.DATABASE = tmpdb

    # Re-initialize the schema in the temp DB
    app_module.init_db()

    app_module.app.config["TESTING"] = True

    with app_module.app.test_client() as client:
        yield client

    # Cleanup
    os.unlink(tmpdb)
    app_module.DATABASE = original_db


class TestHealthEndpoint:
    """Tests for the health check endpoint."""

    def test_health_returns_200(self, client):
        """Given the health endpoint, when called, then returns 200 with status ok."""
        resp = client.get("/health")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["status"] == "ok"


class TestCreateBook:
    """Tests for creating books."""

    def test_create_book_success(self, client):
        """Given valid book data, when POST /books, then returns 201 with the book."""
        payload = {
            "title": "The Great Gatsby",
            "author": "F. Scott Fitzgerald",
            "year": 1925,
            "isbn": "978-0743273565",
        }
        resp = client.post(
            "/books", data=json.dumps(payload), content_type="application/json"
        )
        assert resp.status_code == 201
        data = json.loads(resp.data)
        assert data["title"] == "The Great Gatsby"
        assert data["author"] == "F. Scott Fitzgerald"
        assert data["year"] == 1925
        assert data["isbn"] == "978-0743273565"
        assert "id" in data

    def test_create_book_missing_title(self, client):
        """Given no title, when POST /books, then returns 400."""
        payload = {"author": "Someone", "year": 2000}
        resp = client.post(
            "/books", data=json.dumps(payload), content_type="application/json"
        )
        assert resp.status_code == 400
        data = json.loads(resp.data)
        assert "error" in data

    def test_create_book_missing_author(self, client):
        """Given no author, when POST /books, then returns 400."""
        payload = {"title": "Some Book", "year": 2000}
        resp = client.post(
            "/books", data=json.dumps(payload), content_type="application/json"
        )
        assert resp.status_code == 400
        data = json.loads(resp.data)
        assert "error" in data

    def test_create_book_minimal(self, client):
        """Given only title and author, when POST /books, then returns 201."""
        payload = {"title": "Minimal Book", "author": "Author"}
        resp = client.post(
            "/books", data=json.dumps(payload), content_type="application/json"
        )
        assert resp.status_code == 201
        data = json.loads(resp.data)
        assert data["title"] == "Minimal Book"
        assert data["year"] is None


class TestListBooks:
    """Tests for listing books."""

    def test_list_books_empty(self, client):
        """Given no books, when GET /books, then returns empty list."""
        resp = client.get("/books")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data == []

    def test_list_books_with_filter(self, client):
        """Given multiple books, when GET /books?author=fitzgerald, then returns matching books."""
        # Create two books
        client.post(
            "/books",
            data=json.dumps({"title": "Book A", "author": "Alice Smith"}),
            content_type="application/json",
        )
        client.post(
            "/books",
            data=json.dumps({"title": "Book B", "author": "Bob Jones"}),
            content_type="application/json",
        )
        client.post(
            "/books",
            data=json.dumps(
                {"title": "Book C", "author": "Alice Brown"}
            ),
            content_type="application/json",
        )

        resp = client.get("/books?author=Alice")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert len(data) == 2
        for book in data:
            assert "Alice" in book["author"]

    def test_list_books_all(self, client):
        """Given multiple books, when GET /books, then returns all books."""
        client.post(
            "/books",
            data=json.dumps({"title": "Book A", "author": "Alice"}),
            content_type="application/json",
        )
        client.post(
            "/books",
            data=json.dumps({"title": "Book B", "author": "Bob"}),
            content_type="application/json",
        )
        resp = client.get("/books")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert len(data) == 2


class TestGetBook:
    """Tests for getting a single book."""

    def test_get_book_not_found(self, client):
        """Given a non-existent ID, when GET /books/{id}, then returns 404."""
        resp = client.get("/books/9999")
        assert resp.status_code == 404

    def test_get_book_success(self, client):
        """Given a book exists, when GET /books/{id}, then returns the book."""
        resp = client.post(
            "/books",
            data=json.dumps(
                {"title": "Test Book", "author": "Test Author", "year": 2020}
            ),
            content_type="application/json",
        )
        book_id = json.loads(resp.data)["id"]

        resp = client.get(f"/books/{book_id}")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["title"] == "Test Book"


class TestUpdateBook:
    """Tests for updating a book."""

    def test_update_book_success(self, client):
        """Given a book exists, when PUT /books/{id}, then returns updated book."""
        resp = client.post(
            "/books",
            data=json.dumps({"title": "Old Title", "author": "Old Author"}),
            content_type="application/json",
        )
        book_id = json.loads(resp.data)["id"]

        resp = client.put(
            f"/books/{book_id}",
            data=json.dumps({"title": "New Title", "author": "New Author"}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["title"] == "New Title"
        assert data["author"] == "New Author"

    def test_update_book_not_found(self, client):
        """Given a non-existent ID, when PUT /books/{id}, then returns 404."""
        resp = client.put(
            "/books/9999",
            data=json.dumps({"title": "New", "author": "Author"}),
            content_type="application/json",
        )
        assert resp.status_code == 404


class TestDeleteBook:
    """Tests for deleting a book."""

    def test_delete_book_success(self, client):
        """Given a book exists, when DELETE /books/{id}, then returns 200 and book is gone."""
        resp = client.post(
            "/books",
            data=json.dumps({"title": "To Delete", "author": "Author"}),
            content_type="application/json",
        )
        book_id = json.loads(resp.data)["id"]

        resp = client.delete(f"/books/{book_id}")
        assert resp.status_code == 200

        resp = client.get(f"/books/{book_id}")
        assert resp.status_code == 404

    def test_delete_book_not_found(self, client):
        """Given a non-existent ID, when DELETE /books/{id}, then returns 404."""
        resp = client.delete("/books/9999")
        assert resp.status_code == 404
