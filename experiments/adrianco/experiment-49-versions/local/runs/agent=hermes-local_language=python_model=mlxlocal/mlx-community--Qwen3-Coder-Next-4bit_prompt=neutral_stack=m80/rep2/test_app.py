"""Integration tests for Book API REST service."""

import pytest
import json
import os
import sys

# Add the current directory to the path to import app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, init_db, DATABASE


@pytest.fixture
def client():
    """Create a test client for the app."""
    app.config['TESTING'] = True
    client = app.test_client()
    
    # Initialize a fresh database for testing
    if os.path.exists(DATABASE):
        os.remove(DATABASE)
    init_db()
    
    yield client
    
    # Cleanup
    if os.path.exists(DATABASE):
        os.remove(DATABASE)


def test_health_check(client):
    """Test the health check endpoint."""
    response = client.get('/health')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'healthy'
    assert 'timestamp' in data


def test_get_books_empty(client):
    """Test getting books when database is empty."""
    response = client.get('/books')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data == []


def test_create_book(client):
    """Test creating a new book."""
    book_data = {
        'title': 'The Great Gatsby',
        'author': 'F. Scott Fitzgerald',
        'year': 1925,
        'isbn': '978-0743273565'
    }
    
    response = client.post('/books', 
                           data=json.dumps(book_data),
                           content_type='application/json')
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data['title'] == 'The Great Gatsby'
    assert data['author'] == 'F. Scott Fitzgerald'
    assert data['year'] == 1925
    assert data['isbn'] == '978-0743273565'
    assert 'id' in data


def test_create_book_missing_title(client):
    """Test creating a book without title (should fail)."""
    book_data = {
        'author': 'Some Author',
        'year': 2020
    }
    
    response = client.post('/books', 
                           data=json.dumps(book_data),
                           content_type='application/json')
    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'error' in data
    assert any('title' in err for err in data['error'])


def test_create_book_missing_author(client):
    """Test creating a book without author (should fail)."""
    book_data = {
        'title': 'Some Book',
        'year': 2020
    }
    
    response = client.post('/books', 
                           data=json.dumps(book_data),
                           content_type='application/json')
    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'error' in data
    assert any('author' in err for err in data['error'])


def test_get_book_by_id(client):
    """Test getting a single book by ID."""
    # First create a book
    book_data = {
        'title': '1984',
        'author': 'George Orwell',
        'year': 1949
    }
    
    create_response = client.post('/books',
                                  data=json.dumps(book_data),
                                  content_type='application/json')
    book_id = json.loads(create_response.data)['id']
    
    # Then get the book
    response = client.get(f'/books/{book_id}')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['title'] == '1984'
    assert data['author'] == 'George Orwell'


def test_get_book_not_found(client):
    """Test getting a book that doesn't exist."""
    response = client.get('/books/99999')
    assert response.status_code == 404


def test_update_book(client):
    """Test updating a book."""
    # First create a book
    book_data = {
        'title': 'Original Title',
        'author': 'Original Author',
        'year': 2000
    }
    
    create_response = client.post('/books',
                                  data=json.dumps(book_data),
                                  content_type='application/json')
    book_id = json.loads(create_response.data)['id']
    
    # Update the book
    update_data = {
        'title': 'Updated Title',
        'year': 2020
    }
    
    response = client.put(f'/books/{book_id}',
                          data=json.dumps(update_data),
                          content_type='application/json')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['title'] == 'Updated Title'
    assert data['author'] == 'Original Author'  # Should remain unchanged
    assert data['year'] == 2020


def test_update_book_not_found(client):
    """Test updating a book that doesn't exist."""
    update_data = {
        'title': 'Updated Title'
    }
    
    response = client.put('/books/99999',
                          data=json.dumps(update_data),
                          content_type='application/json')
    assert response.status_code == 404


def test_delete_book(client):
    """Test deleting a book."""
    # First create a book
    book_data = {
        'title': 'To Delete',
        'author': 'Author Name'
    }
    
    create_response = client.post('/books',
                                  data=json.dumps(book_data),
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
    """Test deleting a book that doesn't exist."""
    response = client.delete('/books/99999')
    assert response.status_code == 404


def test_get_books_with_filter(client):
    """Test filtering books by author."""
    # Create books
    books = [
        {'title': 'Book 1', 'author': 'Author A', 'year': 2000},
        {'title': 'Book 2', 'author': 'Author B', 'year': 2001},
        {'title': 'Book 3', 'author': 'Author A', 'year': 2002},
    ]
    
    for book in books:
        client.post('/books', data=json.dumps(book), content_type='application/json')
    
    # Filter by author
    response = client.get('/books?author=Author%20A')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) == 2
    for book in data:
        assert book['author'] == 'Author A'


def test_get_books_no_filter(client):
    """Test getting all books without filter."""
    # Create books
    books = [
        {'title': 'Book 1', 'author': 'Author A'},
        {'title': 'Book 2', 'author': 'Author B'},
        {'title': 'Book 3', 'author': 'Author C'},
    ]
    
    for book in books:
        client.post('/books', data=json.dumps(book), content_type='application/json')
    
    # Get all books
    response = client.get('/books')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) == 3


def test_update_book_partial(client):
    """Test updating a book with partial data."""
    # First create a book
    book_data = {
        'title': 'Complete Title',
        'author': 'Complete Author',
        'year': 2010,
        'isbn': '1234567890'
    }
    
    create_response = client.post('/books',
                                  data=json.dumps(book_data),
                                  content_type='application/json')
    book_id = json.loads(create_response.data)['id']
    
    # Update only title
    update_data = {
        'title': 'New Title Only'
    }
    
    response = client.put(f'/books/{book_id}',
                          data=json.dumps(update_data),
                          content_type='application/json')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['title'] == 'New Title Only'
    assert data['author'] == 'Complete Author'
    assert data['year'] == 2010
    assert data['isbn'] == '1234567890'


def test_create_book_with_only_required_fields(client):
    """Test creating a book with only required fields (title and author)."""
    book_data = {
        'title': 'Minimal Book',
        'author': 'Minimal Author'
    }
    
    response = client.post('/books',
                           data=json.dumps(book_data),
                           content_type='application/json')
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data['title'] == 'Minimal Book'
    assert data['author'] == 'Minimal Author'
    assert data.get('year') is None
    assert data.get('isbn') is None


def test_create_book_invalid_year(client):
    """Test creating a book with invalid year."""
    book_data = {
        'title': 'Book',
        'author': 'Author',
        'year': 'invalid'
    }
    
    response = client.post('/books',
                           data=json.dumps(book_data),
                           content_type='application/json')
    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'error' in data


def test_create_book_empty_title(client):
    """Test creating a book with empty title."""
    book_data = {
        'title': '',
        'author': 'Author'
    }
    
    response = client.post('/books',
                           data=json.dumps(book_data),
                           content_type='application/json')
    assert response.status_code == 400


def test_create_book_empty_author(client):
    """Test creating a book with empty author."""
    book_data = {
        'title': 'Book',
        'author': '   '
    }
    
    response = client.post('/books',
                           data=json.dumps(book_data),
                           content_type='application/json')
    assert response.status_code == 400


def test_create_book_whitespace_title(client):
    """Test creating a book with whitespace-only title."""
    book_data = {
        'title': '   ',
        'author': 'Author'
    }
    
    response = client.post('/books',
                           data=json.dumps(book_data),
                           content_type='application/json')
    assert response.status_code == 400


def test_create_book_whitespace_author(client):
    """Test creating a book with whitespace-only author."""
    book_data = {
        'title': 'Book',
        'author': '   '
    }
    
    response = client.post('/books',
                           data=json.dumps(book_data),
                           content_type='application/json')
    assert response.status_code == 400


def test_update_book_whitespace_title(client):
    """Test updating a book with whitespace-only title."""
    # First create a book
    book_data = {
        'title': 'Original Title',
        'author': 'Original Author'
    }
    
    create_response = client.post('/books',
                                  data=json.dumps(book_data),
                                  content_type='application/json')
    book_id = json.loads(create_response.data)['id']
    
    # Update with whitespace title
    update_data = {
        'title': '   '
    }
    
    response = client.put(f'/books/{book_id}',
                          data=json.dumps(update_data),
                          content_type='application/json')
    assert response.status_code == 400


def test_update_book_whitespace_author(client):
    """Test updating a book with whitespace-only author."""
    # First create a book
    book_data = {
        'title': 'Original Title',
        'author': 'Original Author'
    }
    
    create_response = client.post('/books',
                                  data=json.dumps(book_data),
                                  content_type='application/json')
    book_id = json.loads(create_response.data)['id']
    
    # Update with whitespace author
    update_data = {
        'author': '   '
    }
    
    response = client.put(f'/books/{book_id}',
                          data=json.dumps(update_data),
                          content_type='application/json')
    assert response.status_code == 400


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
