import pytest
import json
import sys
import os

# Add the project root to sys.path so we can import app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_health_endpoint(client):
    """Test the health check endpoint"""
    response = client.get('/health')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'healthy'

def test_create_book_success(client):
    """Test successful book creation"""
    book_data = {
        "title": "Test Book",
        "author": "Test Author", 
        "year": 2023,
        "isbn": "1234567890"
    }
    response = client.post('/books', json=book_data)
    assert response.status_code == 201
    data = json.loads(response.data)
    assert 'id' in data
    assert data['message'] == 'Book created successfully'

def test_create_book_missing_title(client):
    """Test creating book with missing title"""
    book_data = {
        "author": "Test Author",
        "year": 2023
    }
    response = client.post('/books', json=book_data)
    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'error' in data
    assert 'title' in data['error'].lower()

def test_create_book_missing_author(client):
    """Test creating book with missing author"""
    book_data = {
        "title": "Test Book",
        "year": 2023
    }
    response = client.post('/books', json=book_data)
    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'error' in data
    assert 'author' in data['error'].lower()

def test_get_all_books(client):
    """Test getting all books"""
    response = client.get('/books')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert isinstance(data, list)

def test_get_single_book_exists(client):
    """Test getting a single existing book"""
    # First create a book to get its ID
    book_data = {
        "title": "Test Book",
        "author": "Test Author",
        "year": 2023,
        "isbn": "1234567890"
    }
    create_response = client.post('/books', json=book_data)
    data = json.loads(create_response.data)
    book_id = data['id']
    
    response = client.get(f'/books/{book_id}')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['title'] == book_data['title']
    assert data['author'] == book_data['author']

def test_get_nonexistent_book(client):
    """Test getting a non-existent book"""
    response = client.get('/books/999')
    assert response.status_code == 404
    data = json.loads(response.data)
    assert 'error' in data

def test_update_book_success(client):
    """Test updating a book"""
    # First create a book
    book_data = {
        "title": "Test Book",
        "author": "Test Author", 
        "year": 2023,
        "isbn": "1234567890"
    }
    create_response = client.post('/books', json=book_data)
    data = json.loads(create_response.data)
    book_id = data['id']
    
    # Update the book
    update_data = {
        "title": "Updated Test Book",
        "year": 2024
    }
    response = client.put(f'/books/{book_id}', json=update_data)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['message'] == 'Book updated successfully'

def test_delete_book_success(client):
    """Test deleting a book"""
    # First create a book
    book_data = {
        "title": "Test Book",
        "author": "Test Author", 
        "year": 2023,
        "isbn": "1234567890"
    }
    create_response = client.post('/books', json=book_data)
    data = json.loads(create_response.data)
    book_id = data['id']
    
    # Delete the book
    response = client.delete(f'/books/{book_id}')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['message'] == 'Book deleted successfully'

def test_get_all_books_with_filter(client):
    """Test filtering books by author"""
    response = client.get('/books?author=Test')
    assert response.status_code == 200