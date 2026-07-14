"""Tests for Book API REST Service."""

import os
import sys
import pytest
import tempfile
import json

# Ensure the app module can be imported from the current directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import app as book_app


@pytest.fixture
def client():
    """Create a test client with a temporary database."""
    book_app.app.config["TESTING"] = True

    # Use a temporary database for tests
    tmpfd, tmpdb = tempfile.mkstemp(suffix=".db")
    os.close(tmpfd)
    book_app.DATABASE = tmpdb

    # Initialize the database
    book_app.init_db()

    with book_app.app.test_client() as client:
        yield client

    # Cleanup
    os.unlink(tmpdb)


# ── Health check tests ──────────────────────────────────────────────────────

class TestHealthCheck:
    """Tests for the /health endpoint."""

    def test_health_returns_ok(self, client):
        """Given the health endpoint exists, When I call GET /health, Then it returns status ok."""
        response = client.get("/health")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["status"] == "ok"


# ── Create book tests ───────────────────────────────────────────────────────

class TestCreateBook:
    """Tests for the POST /books endpoint."""

    def test_create_book_success(self, client):
        """Given no books exist, When I POST a valid book, Then it returns 201 with the book data."""
        payload = {
            "title": "The Great Gatsby",
            "author": "F. Scott Fitzgerald",
            "year": 1925,
            "isbn": "978-0743273565"
        }
        response = client.post(
            "/books",
            data=json.dumps(payload),
            content_type="application/json"
        )
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data["title"] == "The Great Gatsby"
        assert data["author"] == "F. Scott Fitzgerald"
        assert data["year"] == 1925
        assert data["isbn"] == "978-0743273565"
        assert "id" in data

    def test_create_book_missing_title(self, client):
        """Given no books exist, When I POST without title, Then it returns 400 with error."""
        payload = {
            "author": "F. Scott Fitzgerald",
            "year": 1925
        }
        response = client.post(
            "/books",
            data=json.dumps(payload),
            content_type="application/json"
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data

    def test_create_book_missing_author(self, client):
        """Given no books exist, When I POST without author, Then it returns 400 with error."""
        payload = {
            "title": "The Great Gatsby",
            "year": 1925
        }
        response = client.post(
            "/books",
            data=json.dumps(payload),
            content_type="application/json"
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data

    def test_create_book_no_body(self, client):
        """Given no books exist, When I POST with no JSON body, Then it returns 400."""
        response = client.post(
            "/books",
            data=json.dumps({}),
            content_type="application/json"
        )
        assert response.status_code == 400


# ── List books tests ────────────────────────────────────────────────────────

class TestListBooks:
    """Tests for the GET /books endpoint."""

    def test_list_books_empty(self, client):
        """Given no books exist, When I GET /books, Then it returns an empty list."""
        response = client.get("/books")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data == []

    def test_list_books_with_data(self, client):
        """Given 3 books exist, When I GET /books, Then it returns all 3 books."""
        # Create 3 books
        for i in range(3):
            client.post(
                "/books",
                data=json.dumps({
                    "title": f"Book {i}",
                    "author": f"Author {i}",
                    "year": 2020 + i
                }),
                content_type="application/json"
            )

        response = client.get("/books")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data) == 3

    def test_list_books_filter_by_author(self, client):
        """Given 3 books by different authors, When I GET /books?author=Author1, Then it returns only Author1's books."""
        # Create books
        client.post(
            "/books",
            data=json.dumps({"title": "Book A", "author": "Author1", "year": 2020}),
            content_type="application/json"
        )
        client.post(
            "/books",
            data=json.dumps({"title": "Book B", "author": "Author2", "year": 2021}),
            content_type="application/json"
        )
        client.post(
            "/books",
            data=json.dumps({"title": "Book C", "author": "Author1", "year": 2022}),
            content_type="application/json"
        )

        response = client.get("/books?author=Author1")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data) == 2
        for book in data:
            assert book["author"] == "Author1"


# ── Get single book tests ───────────────────────────────────────────────────

class TestGetBook:
    """Tests for the GET /books/{id} endpoint."""

    def test_get_book_success(self, client):
        """Given a book exists, When I GET /books/1, Then it returns the book."""
        client.post(
            "/books",
            data=json.dumps({
                "title": "1984",
                "author": "George Orwell",
                "year": 1949
            }),
            content_type="application/json"
        )
        response = client.get("/books/1")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["title"] == "1984"
        assert data["author"] == "George Orwell"

    def test_get_book_not_found(self, client):
        """Given no book with id 999, When I GET /books/999, Then it returns 404."""
        response = client.get("/books/999")
        assert response.status_code == 404
        data = json.loads(response.data)
        assert "error" in data


# ── Update book tests ───────────────────────────────────────────────────────

class TestUpdateBook:
    """Tests for the PUT /books/{id} endpoint."""

    def test_update_book_success(self, client):
        """Given a book exists, When I PUT updated data, Then it returns the updated book."""
        # Create a book first
        client.post(
            "/books",
            data=json.dumps({
                "title": "Old Title",
                "author": "Old Author",
                "year": 2000
            }),
            content_type="application/json"
        )

        response = client.put(
            "/books/1",
            data=json.dumps({
                "title": "New Title",
                "author": "New Author",
                "year": 2024
            }),
            content_type="application/json"
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["title"] == "New Title"
        assert data["author"] == "New Author"
        assert data["year"] == 2024

    def test_update_book_not_found(self, client):
        """Given no book with id 999, When I PUT /books/999, Then it returns 404."""
        response = client.put(
            "/books/999",
            data=json.dumps({"title": "X", "author": "Y"}),
            content_type="application/json"
        )
        assert response.status_code == 404

    def test_update_book_partial(self, client):
        """Given a book exists, When I PUT with only author, Then it updates only author and keeps title."""
        client.post(
            "/books",
            data=json.dumps({
                "title": "Old Title",
                "author": "Old Author"
            }),
            content_type="application/json"
        )
        response = client.put(
            "/books/1",
            data=json.dumps({"author": "New Author"}),
            content_type="application/json"
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["title"] == "Old Title"
        assert data["author"] == "New Author"

    def test_update_book_invalid_year(self, client):
        """Given a book exists, When I PUT with non-integer year, Then it returns 400."""
        client.post(
            "/books",
            data=json.dumps({
                "title": "Old Title",
                "author": "Old Author"
            }),
            content_type="application/json"
        )
        response = client.put(
            "/books/1",
            data=json.dumps({"title": "New Title", "author": "New Author", "year": "not-a-number"}),
            content_type="application/json"
        )
        assert response.status_code == 400


# ── Delete book tests ───────────────────────────────────────────────────────

class TestDeleteBook:
    """Tests for the DELETE /books/{id} endpoint."""

    def test_delete_book_success(self, client):
        """Given a book exists, When I DELETE /books/1, Then it returns 200 and the book is gone."""
        client.post(
            "/books",
            data=json.dumps({
                "title": "To Delete",
                "author": "Someone"
            }),
            content_type="application/json"
        )

        response = client.delete("/books/1")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "message" in data

        # Verify it's gone
        response = client.get("/books/1")
        assert response.status_code == 404

    def test_delete_book_not_found(self, client):
        """Given no book with id 999, When I DELETE /books/999, Then it returns 404."""
        response = client.delete("/books/999")
        assert response.status_code == 404
