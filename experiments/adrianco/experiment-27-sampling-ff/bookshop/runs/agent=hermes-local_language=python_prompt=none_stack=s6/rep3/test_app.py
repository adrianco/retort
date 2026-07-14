import os
import sys
import tempfile
import pytest

# Import the app module
import app as book_app


@pytest.fixture
def client():
    """Create a test client with a temporary SQLite database."""
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    book_app.DATABASE = db_path
    book_app.init_db()

    with book_app.app.test_client() as client:
        yield client

    os.close(db_fd)
    os.unlink(db_path)


# ---------- Health check ----------

def test_health(client):
    """GET /health returns 200 with status ok."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "ok"


# ---------- Create a book ----------

def test_create_book(client):
    """POST /books creates a book and returns 201."""
    data = {
        "title": "The Great Gatsby",
        "author": "F. Scott Fitzgerald",
        "year": 1925,
        "isbn": "978-0743273565",
    }
    response = client.post("/books", json=data)
    assert response.status_code == 201
    json_data = response.get_json()
    assert json_data["title"] == "The Great Gatsby"
    assert json_data["author"] == "F. Scott Fitzgerald"
    assert json_data["year"] == 1925
    assert json_data["isbn"] == "978-0743273565"
    assert "id" in json_data


def test_create_book_missing_title(client):
    """POST /books without title returns 400."""
    data = {"author": "Someone", "year": 2000}
    response = client.post("/books", json=data)
    assert response.status_code == 400
    json_data = response.get_json()
    assert "error" in json_data


def test_create_book_missing_author(client):
    """POST /books without author returns 400."""
    data = {"title": "Some Book", "year": 2000}
    response = client.post("/books", json=data)
    assert response.status_code == 400
    json_data = response.get_json()
    assert "error" in json_data


# ---------- List books ----------

def test_list_books_empty(client):
    """GET /books returns empty list when no books exist."""
    response = client.get("/books")
    assert response.status_code == 200
    assert response.get_json() == []


def test_list_books_with_data(client):
    """GET /books returns all books."""
    # Create two books
    client.post("/books", json={"title": "Book A", "author": "Author X", "year": 2020})
    client.post("/books", json={"title": "Book B", "author": "Author Y", "year": 2021})

    response = client.get("/books")
    assert response.status_code == 200
    books = response.get_json()
    assert len(books) == 2


def test_list_books_filter_by_author(client):
    """GET /books?author= filters correctly."""
    client.post("/books", json={"title": "Book A", "author": "Author X", "year": 2020})
    client.post("/books", json={"title": "Book B", "author": "Author X", "year": 2021})
    client.post("/books", json={"title": "Book C", "author": "Author Y", "year": 2022})

    response = client.get("/books?author=Author X")
    assert response.status_code == 200
    books = response.get_json()
    assert len(books) == 2
    for book in books:
        assert book["author"] == "Author X"


# ---------- Get a single book ----------

def test_get_book(client):
    """GET /books/<id> returns the book."""
    resp = client.post("/books", json={"title": "1984", "author": "George Orwell", "year": 1949})
    book_id = resp.get_json()["id"]

    response = client.get(f"/books/{book_id}")
    assert response.status_code == 200
    data = response.get_json()
    assert data["title"] == "1984"


def test_get_book_not_found(client):
    """GET /books/<id> returns 404 for nonexistent book."""
    response = client.get("/books/9999")
    assert response.status_code == 404


# ---------- Update a book ----------

def test_update_book(client):
    """PUT /books/<id> updates the book."""
    resp = client.post("/books", json={"title": "Old Title", "author": "Old Author", "year": 2000})
    book_id = resp.get_json()["id"]

    response = client.put(f"/books/{book_id}", json={"title": "New Title", "year": 2024})
    assert response.status_code == 200
    data = response.get_json()
    assert data["title"] == "New Title"
    assert data["author"] == "Old Author"  # unchanged
    assert data["year"] == 2024


def test_update_book_not_found(client):
    """PUT /books/<id> returns 404 for nonexistent book."""
    response = client.put("/books/9999", json={"title": "Ghost"})
    assert response.status_code == 404


# ---------- Delete a book ----------

def test_delete_book(client):
    """DELETE /books/<id> deletes the book."""
    resp = client.post("/books", json={"title": "To Delete", "author": "Author"})
    book_id = resp.get_json()["id"]

    response = client.delete(f"/books/{book_id}")
    assert response.status_code == 200
    assert response.get_json()["message"] == "Book deleted"

    # Verify it's gone
    response = client.get(f"/books/{book_id}")
    assert response.status_code == 404


def test_delete_book_not_found(client):
    """DELETE /books/<id> returns 404 for nonexistent book."""
    response = client.delete("/books/9999")
    assert response.status_code == 404
