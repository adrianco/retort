"""Integration tests for Book Collection REST API."""

import pytest
import os
import json
import sqlite3

# Set up test database
os.environ['TESTING'] = '1'
from app import app, init_db, DATABASE


@pytest.fixture
def client():
    """Create a test client and initialize test database."""
    # Use a separate test database
    test_db = 'test_books.db'
    
    # Clean up any existing test database
    if os.path.exists(test_db):
        os.remove(test_db)
    
    # Create test app with test database
    app.config['TESTING'] = True
    client = app.test_client()
    
    # Initialize test database
    conn = sqlite3.connect(test_db)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER,
            isbn TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT
        )
    ''')
    conn.commit()
    conn.close()
    
    # Temporarily override DATABASE for tests
    original_db = DATABASE
    import app as app_module
    app_module.DATABASE = test_db
    
    yield client
    
    # Cleanup
    if os.path.exists(test_db):
        os.remove(test_db)
    app_module.DATABASE = original_db


@pytest.fixture
def sample_book():
    """Return sample book data."""
    return {
        'title': 'The Great Gatsby',
        'author': 'F. Scott Fitzgerald',
        'year': 1925,
        'isbn': '978-0743273565'
    }


def test_health_check(client):
    """Test health check endpoint."""
    response = client.get('/health')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'healthy'


def test_create_book(client, sample_book):
    """Test creating a new book."""
    response = client.post('/books', 
                          data=json.dumps(sample_book),
                          content_type='application/json')
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data['title'] == sample_book['title']
    assert data['author'] == sample_book['author']
    assert data['year'] == sample_book['year']
    assert data['isbn'] == sample_book['isbn']
    assert 'id' in data
    assert 'created_at' in data
    assert 'updated_at' in data


def test_create_book_missing_title(client, sample_book):
    """Test creating a book without title returns error."""
    sample_book['title'] = ''
    response = client.post('/books', 
                          data=json.dumps(sample_book),
                          content_type='application/json')
    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'error' in data


def test_create_book_missing_author(client, sample_book):
    """Test creating a book without author returns error."""
    sample_book['author'] = ''
    response = client.post('/books', 
                          data=json.dumps(sample_book),
                          content_type='application/json')
    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'error' in data


def test_list_books_empty(client):
    """Test listing books when database is empty."""
    response = client.get('/books')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert isinstance(data, list)
    assert len(data) == 0


def test_list_books_with_data(client, sample_book):
    """Test listing books with data in database."""
    # First create a book
    create_response = client.post('/books', 
                                  data=json.dumps(sample_book),
                                  content_type='application/json')
    assert create_response.status_code == 201
    
    # Then list books
    response = client.get('/books')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) == 1
    assert data[0]['title'] == sample_book['title']


def test_list_books_filter_by_author(client, sample_book):
    """Test filtering books by author."""
    # Create two books with different authors
    book1 = {**sample_book, 'author': 'Author One'}
    book2 = {**sample_book, 'title': 'Another Book', 'author': 'Author Two'}
    
    client.post('/books', data=json.dumps(book1), content_type='application/json')
    client.post('/books', data=json.dumps(book2), content_type='application/json')
    
    # Filter by author
    response = client.get('/books?author=Author%20One')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) == 1
    assert data[0]['author'] == 'Author One'


def test_get_book_by_id(client, sample_book):
    """Test getting a single book by ID."""
    # Create a book
    create_response = client.post('/books', 
                                  data=json.dumps(sample_book),
                                  content_type='application/json')
    assert create_response.status_code == 201
    book_id = json.loads(create_response.data)['id']
    
    # Get the book
    response = client.get(f'/books/{book_id}')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['id'] == book_id
    assert data['title'] == sample_book['title']


def test_get_book_not_found(client):
    """Test getting a non-existent book returns 404."""
    response = client.get('/books/99999')
    assert response.status_code == 404


def test_update_book(client, sample_book):
    """Test updating a book."""
    # Create a book
    create_response = client.post('/books', 
                                  data=json.dumps(sample_book),
                                  content_type='application/json')
    assert create_response.status_code == 201
    book_id = json.loads(create_response.data)['id']
    
    # Update the book
    updated_data = {
        'title': 'Updated Title',
        'author': sample_book['author'],
        'year': 1926,
        'isbn': '978-0743273565'
    }
    response = client.put(f'/books/{book_id}',
                         data=json.dumps(updated_data),
                         content_type='application/json')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['title'] == 'Updated Title'
    assert data['year'] == 1926


def test_update_book_not_found(client):
    """Test updating a non-existent book returns 404."""
    updated_data = {
        'title': 'Updated Title',
        'author': 'Some Author'
    }
    response = client.put('/books/99999',
                         data=json.dumps(updated_data),
                         content_type='application/json')
    assert response.status_code == 404


def test_delete_book(client, sample_book):
    """Test deleting a book."""
    # Create a book
    create_response = client.post('/books', 
                                  data=json.dumps(sample_book),
                                  content_type='application/json')
    assert create_response.status_code == 201
    book_id = json.loads(create_response.data)['id']
    
    # Delete the book
    response = client.delete(f'/books/{book_id}')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'message' in data
    
    # Verify the book is deleted
    get_response = client.get(f'/books/{book_id}')
    assert get_response.status_code == 404


def test_delete_book_not_found(client):
    """Test deleting a non-existent book returns 404."""
    response = client.delete('/books/99999')
    assert response.status_code == 404


def test_create_book_with_only_required_fields(client):
    """Test creating a book with only required fields (title and author)."""
    minimal_book = {
        'title': 'Minimal Book',
        'author': 'Minimal Author'
    }
    response = client.post('/books', 
                          data=json.dumps(minimal_book),
                          content_type='application/json')
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data['title'] == minimal_book['title']
    assert data['author'] == minimal_book['author']
    assert data.get('year') is None
    assert data.get('isbn') is None


def test_create_book_with_empty_request_body(client):
    """Test creating a book with empty request body."""
    response = client.post('/books', 
                          data='',
                          content_type='application/json')
    assert response.status_code == 400
