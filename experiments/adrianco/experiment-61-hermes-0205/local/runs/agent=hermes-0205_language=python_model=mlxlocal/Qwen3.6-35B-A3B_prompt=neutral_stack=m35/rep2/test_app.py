"""Tests for the Book Collection REST API."""

import os
import sys
import tempfile
import pytest

# Ensure app module is importable
sys.path.insert(0, os.path.dirname(__file__))

import app as app_module


@pytest.fixture
def client():
    """Create a test client with a temporary database."""
    tmpfd, tmpdb = tempfile.mkstemp(suffix=".db")
    os.close(tmpfd)

    app_module.DATABASE = tmpdb
    app_module.init_db()

    client = app_module.app.test_client()

    yield client

    os.unlink(tmpdb)


class TestHealthEndpoint:
    """Tests for the health check endpoint."""

    def test_health_returns_ok(self, client):
        """Given no arguments, when health is checked, then status is ok."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "ok"


class TestCreateBook:
    """Tests for creating books (POST /books)."""

    def test_create_book_success(self, client):
        """Given valid data, when creating a book, then returns 201 with book."""
        payload = {
            "title": "The Great Gatsby",
            "author": "F. Scott Fitzgerald",
            "year": 1925,
            "isbn": "978-0743273565",
        }
        response = client.post("/books", json=payload)
        assert response.status_code == 201
        data = response.get_json()
        assert data["title"] == "The Great Gatsby"
        assert data["author"] == "F. Scott Fitzgerald"
        assert data["year"] == 1925
        assert data["isbn"] == "978-0743273565"
        assert "id" in data

    def test_create_book_missing_title(self, client):
        """Given missing title, when creating a book, then returns 400."""
        payload = {"author": "Someone", "year": 2000}
        response = client.post("/books", json=payload)
        assert response.status_code == 400
        assert "title" in response.get_json()["error"].lower()

    def test_create_book_missing_author(self, client):
        """Given missing author, when creating a book, then returns 400."""
        payload = {"title": "Some Book", "year": 2000}
        response = client.post("/books", json=payload)
        assert response.status_code == 400
        assert "author" in response.get_json()["error"].lower()

    def test_create_book_no_body(self, client):
        """Given no request body, when creating a book, then returns 400."""
        response = client.post("/books", content_type="application/json")
        assert response.status_code == 400


class TestListBooks:
    """Tests for listing books (GET /books)."""

    def test_list_books_empty(self, client):
        """Given no books, when listing, then returns empty list."""
        response = client.get("/books")
        assert response.status_code == 200
        assert response.get_json() == []

    def test_list_books_with_data(self, client):
        """Given some books, when listing, then returns all books."""
        # Create two books
        client.post("/books", json={"title": "Book A", "author": "Author 1"})
        client.post("/books", json={"title": "Book B", "author": "Author 2"})

        response = client.get("/books")
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 2

    def test_list_books_filter_by_author(self, client):
        """Given books by multiple authors, when filtering by author, then returns matching books."""
        client.post("/books", json={"title": "Book A", "author": "Alice"})
        client.post("/books", json={"title": "Book B", "author": "Bob"})
        client.post("/books", json={"title": "Book C", "author": "Alice"})

        response = client.get("/books?author=Alice")
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 2
        for book in data:
            assert "alice" in book["author"].lower()


class TestGetBook:
    """Tests for getting a single book (GET /books/<id>)."""

    def test_get_existing_book(self, client):
        """Given a book exists, when getting by ID, then returns the book."""
        resp = client.post("/books", json={"title": "Test", "author": "Author"})
        book_id = resp.get_json()["id"]

        response = client.get(f"/books/{book_id}")
        assert response.status_code == 200
        assert response.get_json()["title"] == "Test"

    def test_get_nonexistent_book(self, client):
        """Given no book with that ID, when getting by ID, then returns 404."""
        response = client.get("/books/9999")
        assert response.status_code == 404


class TestUpdateBook:
    """Tests for updating a book (PUT /books/<id>)."""

    def test_update_book_success(self, client):
        """Given a book exists, when updating, then returns updated book."""
        resp = client.post("/books", json={"title": "Old Title", "author": "Old Author"})
        book_id = resp.get_json()["id"]

        response = client.put(
            f"/books/{book_id}",
            json={"title": "New Title", "author": "New Author", "year": 2024},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["title"] == "New Title"
        assert data["author"] == "New Author"
        assert data["year"] == 2024

    def test_update_nonexistent_book(self, client):
        """Given no book with that ID, when updating, then returns 404."""
        response = client.put(
            "/books/9999", json={"title": "Ghost", "author": "Nobody"}
        )
        assert response.status_code == 404


class TestDeleteBook:
    """Tests for deleting a book (DELETE /books/<id>)."""

    def test_delete_book_success(self, client):
        """Given a book exists, when deleting, then returns 200 and book is gone."""
        resp = client.post("/books", json={"title": "To Delete", "author": "Author"})
        book_id = resp.get_json()["id"]

        response = client.delete(f"/books/{book_id}")
        assert response.status_code == 200

        get_resp = client.get(f"/books/{book_id}")
        assert get_resp.status_code == 404

    def test_delete_nonexistent_book(self, client):
        """Given no book with that ID, when deleting, then returns 404."""
        response = client.delete("/books/9999")
        assert response.status_code == 404
