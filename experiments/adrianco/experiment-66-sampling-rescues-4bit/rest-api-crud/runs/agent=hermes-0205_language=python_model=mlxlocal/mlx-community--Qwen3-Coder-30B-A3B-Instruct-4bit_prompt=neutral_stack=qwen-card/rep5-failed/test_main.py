import pytest
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import app, init_db
from fastapi.testclient import TestClient
from pydantic import BaseModel
import sqlite3

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_create_book():
    response = client.post("/books", json={
        "title": "Test Book",
        "author": "Test Author",
        "year": 2023,
        "isbn": "1234567890"
    })
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Test Book"
    assert data["author"] == "Test Author"
    assert data["year"] == 2023
    assert data["isbn"] == "1234567890"

def test_get_all_books():
    response = client.get("/books")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    # At least one book (the one created in test_create_book) should exist

def test_get_single_book():
    response = client.post("/books", json={
        "title": "Another Test Book",
        "author": "Another Test Author",
        "year": 2024,
        "isbn": "0987654321"
    })
    
    book_id = response.json()["id"]
    response = client.get(f"/books/{book_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Another Test Book"
    assert data["author"] == "Another Test Author"
    assert data["year"] == 2024
    assert data["isbn"] == "0987654321"

def test_update_book():
    response = client.post("/books", json={
        "title": "Test Book",
        "author": "Test Author"
    })
    
    book_id = response.json()["id"]
    response = client.put(f"/books/{book_id}", json={
        "title": "Updated Test Book",
        "author": "Updated Test Author",
        "year": 2023,
        "isbn": "1234567890"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Test Book"
    assert data["author"] == "Updated Test Author"
    assert data["year"] == 2023
    assert data["isbn"] == "1234567890"

def test_delete_book():
    response = client.post("/books", json={
        "title": "Delete Test Book",
        "author": "Delete Test Author"
    })
    
    book_id = response.json()["id"]
    response = client.delete(f"/books/{book_id}")
    assert response.status_code == 204

def test_get_nonexistent_book():
    response = client.get("/books/99999")
    assert response.status_code == 404

def test_create_book_without_title():
    response = client.post("/books", json={
        "author": "Test Author",
        "year": 2023
    })
    assert response.status_code == 400

def test_create_book_without_author():
    response = client.post("/books", json={
        "title": "Test Book",
        "year": 2023
    })
    assert response.status_code == 400

def test_get_books_by_author():
    response = client.get("/books?author=Test Author")
    assert response.status_code == 200