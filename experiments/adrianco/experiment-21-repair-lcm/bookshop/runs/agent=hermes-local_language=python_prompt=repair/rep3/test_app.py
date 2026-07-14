"""Tests for the Book Collection REST API service."""

import os
import pytest
import sqlite3

from app import app, init_db


@pytest.fixture(autouse=True)
def client():
    """Provide an application client and ensure the DB is initialised."""
    app.config["TESTING"] = True

    # Use a temporary SQLite file so tests are isolated.
    test_db = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_books.db")
    if os.path.exists(test_db):
        os.remove(test_db)

    # Point the app at our test database
    os.environ["DATABASE_PATH"] = test_db

    # Re-import to pick up the new DATABASE_PATH, or just update the module
    import app as app_mod
    app_mod.DATABASE = test_db
    app.DATABASE = test_db

    with app.test_client() as c:
        # Ensure DB exists with schema before each test
        db = sqlite3.connect(test_db)
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                year INTEGER,
                isbn TEXT UNIQUE
            )
            """
        )
        db.commit()
        db.close()
        yield c
        # Cleanup after tests
        if os.path.exists(test_db):
            os.remove(test_db)


# --- R1: POST /books creates a new book ---

def test_create_book(client):
    """A create route accepts the four fields and persists a book."""
    response = client.post(
        "/books",
        json={"title": "The Great Gatsby", "author": "F. Scott Fitzgerald",
              "year": 1925, "isbn": "978-0743273565"},
    )
    assert response.status_code == 201
    data = response.get_json()
    assert data["title"] == "The Great Gatsby"
    assert data["author"] == "F. Scott Fitzgerald"
    assert data["year"] == 1925
    assert data["isbn"] == "978-0743273565"
    assert "id" in data


def test_create_book_missing_title(client):
    """Creating without title is rejected (400)."""
    response = client.post(
        "/books",
        json={"author": "Some Author"},
    )
    assert response.status_code == 400
    assert "title" in response.get_json()["error"].lower()


def test_create_book_missing_author(client):
    """Creating without author is rejected (400)."""
    response = client.post(
        "/books",
        json={"title": "Some Book"},
    )
    assert response.status_code == 400
    assert "author" in response.get_json()["error"].lower()


# --- R2 & R3: GET /books lists all books, supports ?author= filter ---

def test_list_books(client):
    """A list route returns the collection."""
    # Create a book first
    client.post("/books", json={
        "title": "1984", "author": "George Orwell", "year": 1949})
    response = client.get("/books")
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0]["title"] == "1984"


def test_list_books_author_filter(client):
    """The list route filters by author query param."""
    client.post("/books", json={
        "title": "1984", "author": "George Orwell", "year": 1949})
    client.post("/books", json={
        "title": "Brave New World", "author": "Aldous Huxley", "year": 1932})
    response = client.get("/books?author=Orwell")
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 1
    assert data[0]["author"] == "George Orwell"


# --- R4: GET /books/{id} returns a single book by id ---

def test_get_book(client):
    """A get-by-id route returns one book (404 if absent)."""
    # Create a book
    resp = client.post("/books", json={
        "title": "Dune", "author": "Frank Herbert", "year": 1965})
    book_id = resp.get_json()["id"]

    response = client.get(f"/books/{book_id}")
    assert response.status_code == 200
    data = response.get_json()
    assert data["title"] == "Dune"

    # Non-existent id should return 404
    response = client.get("/books/99999")
    assert response.status_code == 404


# --- R5: PUT /books/{id} updates a book ---

def test_update_book(client):
    """An update route modifies an existing book."""
    resp = client.post("/books", json={
        "title": "Old Title", "author": "Old Author", "year": 2000})
    book_id = resp.get_json()["id"]

    response = client.put(f"/books/{book_id}", json={
        "title": "New Title", "author": "New Author", "year": 2020})
    assert response.status_code == 200
    data = response.get_json()
    assert data["title"] == "New Title"
    assert data["author"] == "New Author"
    assert data["year"] == 2020


def test_update_nonexistent_book(client):
    """Updating a non-existent book returns 404."""
    response = client.put("/books/99999", json={
        "title": "Ghost", "author": "Nobody", "year": 2020})
    assert response.status_code == 404


# --- R6: DELETE /books/{id} deletes a book ---

def test_delete_book(client):
    """A delete route removes a book."""
    resp = client.post("/books", json={
        "title": "Temp Book", "author": "Temp Author"})
    book_id = resp.get_json()["id"]

    response = client.delete(f"/books/{book_id}")
    assert response.status_code == 200
    assert response.get_json()["message"] == "Book deleted"

    # Verify it is gone
    response = client.get(f"/books/{book_id}")
    assert response.status_code == 404


def test_delete_nonexistent_book(client):
    """Deleting a non-existent book returns 404."""
    response = client.delete("/books/99999")
    assert response.status_code == 404


# --- R10: GET /health ---

def test_health(client):
    """A /health route returns a healthy status."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "ok"
