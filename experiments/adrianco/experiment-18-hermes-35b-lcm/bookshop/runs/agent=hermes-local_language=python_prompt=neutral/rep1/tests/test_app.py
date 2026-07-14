"""Integration tests for the Book Collection API."""

import os

import pytest
from fastapi.testclient import TestClient
import app


@pytest.fixture(autouse=True)
def _setup_db(tmp_path, monkeypatch):
    """Each test gets a clean temporary database."""
    db_path = str(tmp_path / "test_books.db")
    monkeypatch.setenv("BOOK_DB", db_path)
    app.init_db()


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Fresh client with a clean database for each test."""
    db_path = str(tmp_path / "test_books.db")
    monkeypatch.setenv("BOOK_DB", db_path)
    app.init_db()
    return TestClient(app.app)


# -------------------------------------------------------------------
# Health check
# -------------------------------------------------------------------
def test_health_check(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# -------------------------------------------------------------------
# Create book
# -------------------------------------------------------------------
def _create_book(client, title: str, author: str, year=None, isbn=None):
    payload = {"title": title, "author": author}
    if year is not None:
        payload["year"] = year
    if isbn is not None:
        payload["isbn"] = isbn
    return client.post("/books", json=payload)


def test_create_book_success(client):
    resp = _create_book(client, "1984", "George Orwell", year=1949, isbn="978-0451524935")
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "1984"
    assert data["author"] == "George Orwell"
    assert data["year"] == 1949
    assert data["isbn"] == "978-0451524935"
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


def test_create_book_minimal(client):
    resp = _create_book(client, "Clean Code", "Robert Martin")
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Clean Code"
    assert data["year"] is None
    assert data["isbn"] is None


def test_create_book_missing_title(client):
    resp = client.post("/books", json={"author": "Someone"})
    assert resp.status_code == 422


def test_create_book_missing_author(client):
    resp = client.post("/books", json={"title": "Some Book"})
    assert resp.status_code == 422


def test_create_book_empty_title(client):
    resp = client.post("/books", json={"title": "", "author": "Someone"})
    assert resp.status_code == 422


# -------------------------------------------------------------------
# List books
# -------------------------------------------------------------------
def test_list_books_empty(client):
    resp = client.get("/books")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_books_all(client):
    _create_book(client, "Book A", "Author X")
    _create_book(client, "Book B", "Author Y")
    resp = client.get("/books")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_list_books_filter_by_author(client):
    _create_book(client, "Book A", "Author X")
    _create_book(client, "Book B", "Author X")
    _create_book(client, "Book C", "Author Y")
    resp = client.get("/books?author=Author+X")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert all(b["author"] == "Author X" for b in data)


# -------------------------------------------------------------------
# Get single book
# -------------------------------------------------------------------
def test_get_book_success(client):
    r = _create_book(client, "Dune", "Frank Herbert")
    book_id = r.json()["id"]
    resp = client.get(f"/books/{book_id}")
    assert resp.status_code == 200
    assert resp.json()["title"] == "Dune"


def test_get_book_not_found(client):
    resp = client.get("/books/99999")
    assert resp.status_code == 404


# -------------------------------------------------------------------
# Update book
# -------------------------------------------------------------------
def test_update_book_success(client):
    r = _create_book(client, "Old Title", "Old Author")
    book_id = r.json()["id"]
    resp = client.put(f"/books/{book_id}", json={"title": "New Title"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "New Title"
    assert data["author"] == "Old Author"
    assert data["year"] is None


def test_update_book_not_found(client):
    resp = client.put("/books/99999", json={"title": "Phantom"})
    assert resp.status_code == 404


# -------------------------------------------------------------------
# Delete book
# -------------------------------------------------------------------
def test_delete_book_success(client):
    r = _create_book(client, "To Delete", "Author Z")
    book_id = r.json()["id"]
    resp = client.delete(f"/books/{book_id}")
    assert resp.status_code == 204

    # Confirm gone
    resp = client.get(f"/books/{book_id}")
    assert resp.status_code == 404


def test_delete_book_not_found(client):
    resp = client.delete("/books/99999")
    assert resp.status_code == 404
