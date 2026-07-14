"""Acceptance tests for the Book API REST Service."""

import os
import sys
import json
import pytest
import sqlite3

# Ensure the app module can be imported
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import app as app_module


@pytest.fixture
def client():
    """Create a test client with a fresh in-memory database."""
    app_module.app.config["TESTING"] = True
    # Use a temporary database for tests
    db_path = os.path.join(os.path.dirname(__file__), "test_books.db")
    if os.path.exists(db_path):
        os.remove(db_path)

    old_db = app_module.DATABASE
    app_module.DATABASE = db_path

    app_module.init_db()

    with app_module.app.test_client() as client:
        yield client

    # Cleanup
    if os.path.exists(db_path):
        os.remove(db_path)
    app_module.DATABASE = old_db


# ---------------------------------------------------------------------------
# GIVEN a healthy API, WHEN I check health, THEN I get 200 OK
# ---------------------------------------------------------------------------

class TestHealthEndpoint:
    def test_health_returns_ok(self, client):
        """Given a healthy API, when I check health, then I get 200 OK."""
        response = client.get("/health")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["status"] == "ok"


# ---------------------------------------------------------------------------
# GIVEN an empty collection, WHEN I create a book, THEN I get the book back
# ---------------------------------------------------------------------------

class TestCreateBook:
    def test_create_book_success(self, client):
        """Given an empty collection, when I create a book, then I get the book back with 201."""
        payload = {
            "title": "The Great Gatsby",
            "author": "F. Scott Fitzgerald",
            "year": 1925,
            "isbn": "978-0743273565",
        }
        response = client.post("/books", json=payload)
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data["title"] == "The Great Gatsby"
        assert data["author"] == "F. Scott Fitzgerald"
        assert data["year"] == 1925
        assert data["isbn"] == "978-0743273565"
        assert "id" in data

    def test_create_book_missing_title(self, client):
        """Given a request with no title, when I POST, then I get 400 with error."""
        payload = {"author": "Unknown", "year": 2000}
        response = client.post("/books", json=payload)
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data

    def test_create_book_missing_author(self, client):
        """Given a request with no author, when I POST, then I get 400 with error."""
        payload = {"title": "Some Book"}
        response = client.post("/books", json=payload)
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data


# ---------------------------------------------------------------------------
# GIVEN several books exist, WHEN I list them, THEN I get all books
# ---------------------------------------------------------------------------

class TestListBooks:
    def _seed_books(self, client):
        """Helper to seed a few books."""
        books = [
            {"title": "The Great Gatsby", "author": "F. Scott Fitzgerald", "year": 1925},
            {"title": "1984", "author": "George Orwell", "year": 1949},
            {"title": "Animal Farm", "author": "George Orwell", "year": 1945},
        ]
        for book in books:
            client.post("/books", json=book)

    def test_list_all_books(self, client):
        """Given several books exist, when I GET /books, then I get all of them."""
        self._seed_books(client)
        response = client.get("/books")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data) == 3

    def test_filter_by_author(self, client):
        """Given several books exist, when I filter by author, then I get matching books only."""
        self._seed_books(client)
        response = client.get("/books?author=Orwell")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data) == 2
        for book in data:
            assert "Orwell" in book["author"]


# ---------------------------------------------------------------------------
# GIVEN a book exists, WHEN I get it by ID, THEN I get the book
# ---------------------------------------------------------------------------

class TestGetBook:
    def test_get_existing_book(self, client):
        """Given a book exists, when I GET /books/<id>, then I get the book."""
        payload = {"title": "Dune", "author": "Frank Herbert", "year": 1965}
        create_resp = client.post("/books", json=payload)
        book_id = json.loads(create_resp.data)["id"]

        response = client.get(f"/books/{book_id}")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["title"] == "Dune"

    def test_get_nonexistent_book(self, client):
        """Given no book with that ID, when I GET /books/9999, then I get 404."""
        response = client.get("/books/9999")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# GIVEN a book exists, WHEN I update it, THEN I get the updated book
# ---------------------------------------------------------------------------

class TestUpdateBook:
    def test_update_book_success(self, client):
        """Given a book exists, when I PUT updated data, then I get the updated book."""
        payload = {"title": "Dune", "author": "Frank Herbert", "year": 1965}
        create_resp = client.post("/books", json=payload)
        book_id = json.loads(create_resp.data)["id"]

        update_payload = {"title": "Dune (Updated)", "year": 1965}
        response = client.put(f"/books/{book_id}", json=update_payload)
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["title"] == "Dune (Updated)"
        assert data["author"] == "Frank Herbert"  # unchanged

    def test_update_nonexistent_book(self, client):
        """Given no book with that ID, when I PUT, then I get 404."""
        response = client.put("/books/9999", json={"title": "Ghost"})
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# GIVEN a book exists, WHEN I delete it, THEN I get 200 and it is gone
# ---------------------------------------------------------------------------

class TestDeleteBook:
    def test_delete_book_success(self, client):
        """Given a book exists, when I DELETE /books/<id>, then I get 200 and it is gone."""
        payload = {"title": "Neuromancer", "author": "William Gibson", "year": 1984}
        create_resp = client.post("/books", json=payload)
        book_id = json.loads(create_resp.data)["id"]

        response = client.delete(f"/books/{book_id}")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "message" in data

        # Verify it is actually gone
        get_response = client.get(f"/books/{book_id}")
        assert get_response.status_code == 404

    def test_delete_nonexistent_book(self, client):
        """Given no book with that ID, when I DELETE, then I get 404."""
        response = client.delete("/books/9999")
        assert response.status_code == 404
