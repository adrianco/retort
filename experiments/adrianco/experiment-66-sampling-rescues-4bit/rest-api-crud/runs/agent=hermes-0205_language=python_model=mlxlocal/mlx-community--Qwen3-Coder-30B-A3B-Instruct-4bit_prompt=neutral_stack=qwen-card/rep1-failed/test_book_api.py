import sqlite3
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import pytest
from fastapi.testclient import TestClient

# Import the app from main.py
from main import app

client = TestClient(app)

def test_health_check():
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_create_book():
    """Test creating a book."""
    response = client.post(
        "/books",
        json={
            "title": "The Great Gatsby",
            "author": "F. Scott Fitzgerald",
            "year": 1925,
            "isbn": "978-0743273565"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "The Great Gatsby"
    assert data["author"] == "F. Scott Fitzgerald"
    assert data["year"] == 1925
    assert data["isbn"] == "978-0743273565"

def test_create_book_missing_required_fields():
    """Test creating a book with missing required fields."""
    response = client.post(
        "/books",
        json={
            "title": "The Great Gatsby",
            # Missing author field
        }
    )
    assert response.status_code == 422

def test_get_all_books():
    """Test getting all books."""
    response = client.get("/books")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

def test_get_book_by_id():
    """Test getting a single book by ID."""
    response = client.post(
        "/books",
        json={
            "title": "The Great Gatsby",
            "author": "F. Scott Fitzgerald",
            "year": 1925,
            "isbn": "978-0743273565"
        }
    )
    
    book_id = response.json()["id"]
    
    response = client.get(f"/books/{book_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "The Great Gatsby"
    assert data["author"] == "F. Scott Fitzgerald"
    assert data["year"] == 1925
    assert data["isbn"] == "978-0743273565"

def test_update_book():
    """Test updating a book."""
    response = client.post(
        "/books",
        json={
            "title": "The Great Gatsby",
            "author": "F. Scott Fitzgerald",
            "year": 1925,
            "isbn": "978-0743273565"
        }
    )
    
    book_id = response.json()["id"]
    
    response = client.put(
        f"/books/{book_id}",
        json={
            "title": "Updated Title",
            "year": 1930
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Title"
    assert data["author"] == "F. Scott Fitzgerald"
    assert data["year"] == 1930

def test_delete_book():
    """Test deleting a book."""
    response = client.post(
        "/books",
        json={
            "title": "The Great Gatsby",
            "author": "F. Scott Fitzgerald",
            "year": 1925,
            "isbn": "978-0743273565"
        }
    )
    
    book_id = response.json()["id"]
    
    response = client.delete(f"/books/{book_id}")
    assert response.status_code == 204