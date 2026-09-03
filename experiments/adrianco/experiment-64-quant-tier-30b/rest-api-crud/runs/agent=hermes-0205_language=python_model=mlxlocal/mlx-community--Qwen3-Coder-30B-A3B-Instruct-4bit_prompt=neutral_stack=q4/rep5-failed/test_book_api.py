import pytest
import sqlite3
import requests
import subprocess
import time
import os
import time

# Start the server in background
subprocess.Popen(["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

# Give the server time to start
time.sleep(2)

BASE_URL = "http://localhost:8000"

def test_health_check():
    response = requests.get(f"{BASE_URL}/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_create_book():
    response = requests.post(f"{BASE_URL}/books", json={
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

def test_get_books():
    response = requests.get(f"{BASE_URL}/books")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    # Check that we have at least one book (the one we created)
    assert len(data) >= 1

def test_get_book_by_id():
    response = requests.post(f"{BASE_URL}/books", json={
        "title": "Test Book 2",
        "author": "Test Author 2",
        "year": 2023,
        "isbn": "0987654321"
    })
    assert response.status_code == 201
    book_data = response.json()
    book_id = book_data["id"]
    
    response = requests.get(f"{BASE_URL}/books/{book_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Test Book 2"
    assert data["author"] == "Test Author 2"
    assert data["year"] == 2023
    assert data["isbn"] == "0987654321"

def test_update_book():
    response = requests.post(f"{BASE_URL}/books", json={
        "title": "Test Book",
        "author": "Test Author",
        "year": 2023,
        "isbn": "1234567890"
    })
    assert response.status_code == 201
    book_data = response.json()
    book_id = book_data["id"]
    
    response = requests.put(f"{BASE_URL}/books/{book_id}", json={
        "title": "Updated Test Book",
        "author": "Updated Test Author",
        "year": 2024,
        "isbn": "1234567890"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Test Book"
    assert data["author"] == "Updated Test Author"
    assert data["year"] == 2024
    assert data["isbn"] == "1234567890"

def test_delete_book():
    response = requests.post(f"{BASE_URL}/books", json={
        "title": "Delete Test Book",
        "author": "Delete Test Author",
        "year": 2023,
        "isbn": "0987654321"
    })
    assert response.status_code == 201
    book_data = response.json()
    book_id = book_data["id"]
    
    response = requests.delete(f"{BASE_URL}/books/{book_id}")
    assert response.status_code == 204
    
    # Verify book is deleted
    response = requests.get(f"{BASE_URL}/books/{book_id}")
    assert response.status_code == 404

def test_create_book_with_duplicate_isbn():
    response = requests.post(f"{BASE_URL}/books", json={
        "title": "Test Book",
        "author": "Test Author",
        "year": 2023,
        "isbn": "1234567890"
    })
    assert response.status_code == 201
    
    # Try to create another book with same ISBN
    response = requests.post(f"{BASE_URL}/books", json={
        "title": "Another Test Book",
        "author": "Another Test Author",
        "year": 2024,
        "isbn": "1234567890"
    })
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]

def test_get_books_by_author():
    response = requests.get(f"{BASE_URL}/books?author=Test Author")
    assert response.status_code == 200