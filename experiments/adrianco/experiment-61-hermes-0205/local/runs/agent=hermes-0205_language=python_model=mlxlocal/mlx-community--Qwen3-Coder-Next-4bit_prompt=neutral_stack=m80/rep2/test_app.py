#!/usr/bin/env python3
"""Integration tests for the Book API REST Service."""

import pytest
import json
import os
import sys
import tempfile
import shutil

# Add the current directory to the path to import app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


# Create a fresh app instance for each test
def create_test_app():
    """Create a new app instance with test database."""
    from app import app, init_db
    
    # Create a temporary directory for the test database
    test_db_dir = tempfile.mkdtemp()
    test_db = os.path.join(test_db_dir, 'test_books.db')
    
    app = app.__class__('test')
    app.config['TESTING'] = True
    app.config['DATABASE'] = test_db
    
    # Initialize the database
    init_db()
    
    return app, test_db_dir


@pytest.fixture
def client():
    """Create a test client for the app."""
    from app import init_db
    
    # Create a temporary directory for the test database
    test_db_dir = tempfile.mkdtemp()
    test_db = os.path.join(test_db_dir, 'test_books.db')
    
    # Override the DATABASE constant
    import app as app_module
    original_db = getattr(app_module, 'DATABASE', None)
    setattr(app_module, 'DATABASE', test_db)
    
    # Re-initialize the app with the test database
    from app import app as app_instance
    app_instance.config['TESTING'] = True
    app_instance.config['DATABASE'] = test_db
    
    # Re-run init_db to reset the database
    init_db()
    
    client = app_instance.test_client()
    yield client
    
    # Clean up test database
    try:
        if os.path.exists(test_db):
            os.remove(test_db)
        if os.path.exists(test_db_dir):
            shutil.rmtree(test_db_dir)
    except Exception:
        pass
    
    # Restore original database
    if original_db:
        setattr(app_module, 'DATABASE', original_db)


def test_health_check(client):
    """Test the health check endpoint."""
    response = client.get('/health')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'healthy'
    assert 'timestamp' in data


def test_create_book(client):
    """Test creating a new book."""
    book_data = {
        'title': 'The Great Gatsby',
        'author': 'F. Scott Fitzgerald',
        'year': 1925,
        'isbn': '978-0-7432-7356-5'
    }
    
    response = client.post('/books', 
                           data=json.dumps(book_data),
                           content_type='application/json')
    
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data['title'] == 'The Great Gatsby'
    assert data['author'] == 'F. Scott Fitzgerald'
    assert data['year'] == 1925
    assert data['isbn'] == '978-0-7432-7356-5'
    assert 'id' in data
    assert 'created_at' in data
    assert 'updated_at' in data


def test_create_book_missing_title(client):
    """Test creating a book without title."""
    book_data = {
        'author': 'Some Author',
        'year': 2024
    }
    
    response = client.post('/books', 
                           data=json.dumps(book_data),
                           content_type='application/json')
    
    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'error' in data
    assert 'title' in data['error'].lower()


def test_create_book_missing_author(client):
    """Test creating a book without author."""
    book_data = {
        'title': 'Some Book',
        'year': 2024
    }
    
    response = client.post('/books', 
                           data=json.dumps(book_data),
                           content_type='application/json')
    
    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'error' in data
    assert 'author' in data['error'].lower()


def test_create_book_invalid_year(client):
    """Test creating a book with invalid year."""
    book_data = {
        'title': 'Some Book',
        'author': 'Some Author',
        'year': 'not-a-number'
    }
    
    response = client.post('/books', 
                           data=json.dumps(book_data),
                           content_type='application/json')
    
    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'error' in data


def test_list_books(client):
    """Test listing all books."""
    # Create some books first
    client.post('/books', 
                data=json.dumps({'title': 'Book 1', 'author': 'Author A'}),
                content_type='application/json')
    client.post('/books', 
                data=json.dumps({'title': 'Book 2', 'author': 'Author B'}),
                content_type='application/json')
    
    response = client.get('/books')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert isinstance(data, list)
    assert len(data) == 2


def test_list_books_by_author(client):
    """Test listing books filtered by author."""
    # Create some books
    client.post('/books', 
                data=json.dumps({'title': 'Book 1', 'author': 'Author A'}),
                content_type='application/json')
    client.post('/books', 
                data=json.dumps({'title': 'Book 2', 'author': 'Author B'}),
                content_type='application/json')
    client.post('/books', 
                data=json.dumps({'title': 'Book 3', 'author': 'Author A'}),
                content_type='application/json')
    
    response = client.get('/books?author=Author%20A')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert isinstance(data, list)
    assert len(data) == 2
    assert all(book['author'] == 'Author A' for book in data)


def test_get_book_by_id(client):
    """Test getting a single book by ID."""
    # Create a book
    create_response = client.post('/books', 
                                  data=json.dumps({'title': 'Test Book', 'author': 'Test Author'}),
                                  content_type='application/json')
    book_id = json.loads(create_response.data)['id']
    
    # Get the book
    response = client.get(f'/books/{book_id}')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['title'] == 'Test Book'
    assert data['author'] == 'Test Author'


def test_get_book_not_found(client):
    """Test getting a non-existent book."""
    response = client.get('/books/99999')
    assert response.status_code == 404
    data = json.loads(response.data)
    assert 'error' in data


def test_update_book(client):
    """Test updating a book."""
    # Create a book
    create_response = client.post('/books', 
                                  data=json.dumps({'title': 'Original Title', 'author': 'Original Author'}),
                                  content_type='application/json')
    book_id = json.loads(create_response.data)['id']
    
    # Update the book
    update_data = {
        'title': 'Updated Title',
        'author': 'Updated Author',
        'year': 2025
    }
    
    response = client.put(f'/books/{book_id}', 
                          data=json.dumps(update_data),
                          content_type='application/json')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['title'] == 'Updated Title'
    assert data['author'] == 'Updated Author'
    assert data['year'] == 2025


def test_update_book_partial(client):
    """Test partial update of a book."""
    # Create a book
    create_response = client.post('/books', 
                                  data=json.dumps({'title': 'Original Title', 'author': 'Original Author', 'year': 2020}),
                                  content_type='application/json')
    book_id = json.loads(create_response.data)['id']
    
    # Update only the year
    update_data = {'year': 2025}
    
    response = client.put(f'/books/{book_id}', 
                          data=json.dumps(update_data),
                          content_type='application/json')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['year'] == 2025
    assert data['title'] == 'Original Title'
    assert data['author'] == 'Original Author'


def test_update_book_not_found(client):
    """Test updating a non-existent book."""
    update_data = {'title': 'New Title'}
    
    response = client.put('/books/99999', 
                          data=json.dumps(update_data),
                          content_type='application/json')
    
    assert response.status_code == 404
    data = json.loads(response.data)
    assert 'error' in data


def test_delete_book(client):
    """Test deleting a book."""
    # Create a book
    create_response = client.post('/books', 
                                  data=json.dumps({'title': 'To Delete', 'author': 'Delete Author'}),
                                  content_type='application/json')
    book_id = json.loads(create_response.data)['id']
    
    # Delete the book
    response = client.delete(f'/books/{book_id}')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'deleted' in data['message'].lower() or 'delete' in data['message'].lower()
    
    # Verify the book is gone
    get_response = client.get(f'/books/{book_id}')
    assert get_response.status_code == 404


def test_delete_book_not_found(client):
    """Test deleting a non-existent book."""
    response = client.delete('/books/99999')
    assert response.status_code == 404
    data = json.loads(response.data)
    assert 'error' in data


def test_validation_title_not_string(client):
    """Test validation that title must be a string."""
    book_data = {
        'title': 12345,
        'author': 'Some Author'
    }
    
    response = client.post('/books', 
                           data=json.dumps(book_data),
                           content_type='application/json')
    
    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'error' in data


def test_validation_author_not_string(client):
    """Test validation that author must be a string."""
    book_data = {
        'title': 'Some Book',
        'author': 12345
    }
    
    response = client.post('/books', 
                           data=json.dumps(book_data),
                           content_type='application/json')
    
    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'error' in data


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
