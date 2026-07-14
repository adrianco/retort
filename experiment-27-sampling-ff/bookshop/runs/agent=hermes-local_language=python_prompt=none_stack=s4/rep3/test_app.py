"""Tests for the Book Collection REST API."""

import os
import sys
import tempfile
import pytest

# Ensure the app module can be imported
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import app as app_module


@pytest.fixture
def client():
    """Create a test client with a temporary database."""
    app_module.app.config['TESTING'] = True

    # Use a temporary database for tests
    fd, temp_db = tempfile.mkstemp(suffix='.db')
    os.close(fd)

    app_module.DATABASE = temp_db
    app_module.init_db()

    with app_module.app.test_client() as client:
        yield client

    os.unlink(temp_db)


# --- Health Check Tests ---

def test_health_check(client):
    """Given the application is running, when I call GET /health, then I get a 200 status."""
    response = client.get('/health')
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'healthy'


# --- Create Book Tests ---

def test_create_book_success(client):
    """Given valid book data, when I POST /books, then I get a 201 status with the book."""
    response = client.post('/books', json={
        'title': 'The Great Gatsby',
        'author': 'F. Scott Fitzgerald',
        'year': 1925,
        'isbn': '978-0743273565'
    })
    assert response.status_code == 201
    data = response.get_json()
    assert data['title'] == 'The Great Gatsby'
    assert data['author'] == 'F. Scott Fitzgerald'
    assert data['year'] == 1925
    assert data['isbn'] == '978-0743273565'
    assert 'id' in data


def test_create_book_missing_title(client):
    """Given missing title, when I POST /books, then I get a 400 error."""
    response = client.post('/books', json={
        'author': 'Unknown Author',
        'year': 2020
    })
    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data
    assert 'Title is required' in data['error']


def test_create_book_missing_author(client):
    """Given missing author, when I POST /books, then I get a 400 error."""
    response = client.post('/books', json={
        'title': 'Some Book',
        'year': 2020
    })
    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data
    assert 'Author is required' in data['error']


# --- List Books Tests ---

def test_list_books_empty(client):
    """Given no books exist, when I GET /books, then I get an empty list."""
    response = client.get('/books')
    assert response.status_code == 200
    data = response.get_json()
    assert data == []


def test_list_books_with_filter(client):
    """Given multiple books, when I GET /books?author=Fitzgerald, then I get only matching books."""
    # Create two books
    client.post('/books', json={
        'title': 'The Great Gatsby',
        'author': 'F. Scott Fitzgerald',
        'year': 1925
    })
    client.post('/books', json={
        'title': '1984',
        'author': 'George Orwell',
        'year': 1949
    })

    response = client.get('/books?author=Fitzgerald')
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 1
    assert data[0]['author'] == 'F. Scott Fitzgerald'


# --- Get Book Tests ---

def test_get_book_not_found(client):
    """Given a non-existent book ID, when I GET /books/999, then I get a 404."""
    response = client.get('/books/999')
    assert response.status_code == 404
    data = response.get_json()
    assert 'error' in data


def test_get_book_success(client):
    """Given a book exists, when I GET /books/1, then I get the book."""
    resp = client.post('/books', json={
        'title': 'To Kill a Mockingbird',
        'author': 'Harper Lee',
        'year': 1960,
        'isbn': '978-0061120084'
    })
    book_id = resp.get_json()['id']

    response = client.get(f'/books/{book_id}')
    assert response.status_code == 200
    data = response.get_json()
    assert data['title'] == 'To Kill a Mockingbird'
    assert data['author'] == 'Harper Lee'


# --- Update Book Tests ---

def test_update_book_success(client):
    """Given a book exists, when I PUT /books/1, then I get the updated book."""
    resp = client.post('/books', json={
        'title': 'Original Title',
        'author': 'Original Author',
        'year': 2000
    })
    book_id = resp.get_json()['id']

    response = client.put(f'/books/{book_id}', json={
        'title': 'Updated Title',
        'author': 'Updated Author',
        'year': 2024
    })
    assert response.status_code == 200
    data = response.get_json()
    assert data['title'] == 'Updated Title'
    assert data['author'] == 'Updated Author'
    assert data['year'] == 2024


def test_update_book_not_found(client):
    """Given a non-existent book, when I PUT /books/999, then I get a 404."""
    response = client.put('/books/999', json={
        'title': 'Ghost',
        'author': 'Nobody'
    })
    assert response.status_code == 404


# --- Delete Book Tests ---

def test_delete_book_success(client):
    """Given a book exists, when I DELETE /books/1, then I get 200 and the book is gone."""
    resp = client.post('/books', json={
        'title': 'ToDelete',
        'author': 'Someone',
        'year': 2020
    })
    book_id = resp.get_json()['id']

    response = client.delete(f'/books/{book_id}')
    assert response.status_code == 200
    data = response.get_json()
    assert 'deleted' in data['message'].lower() or 'success' in data['message'].lower()

    # Verify it's gone
    response = client.get(f'/books/{book_id}')
    assert response.status_code == 404


def test_delete_book_not_found(client):
    """Given a non-existent book, when I DELETE /books/999, then I get a 404."""
    response = client.delete('/books/999')
    assert response.status_code == 404
