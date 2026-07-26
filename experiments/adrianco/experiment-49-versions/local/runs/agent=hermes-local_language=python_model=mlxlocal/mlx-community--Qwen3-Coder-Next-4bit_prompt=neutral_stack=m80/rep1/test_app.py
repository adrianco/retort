"""Integration tests for Book Collection REST API."""

import pytest
import json
import os
import tempfile
import shutil
from app import app, init_db, get_db, DATABASE


@pytest.fixture
def client():
    """Create test client with temporary database."""
    db_fd, db_path = tempfile.mkstemp()
    os.close(db_fd)
    
    app.config['TESTING'] = True
    app.config['DATABASE'] = db_path
    
    client = app.test_client()
    
    # Initialize database
    with app.app_context():
        init_db()
    
    yield client
    
    # Cleanup
    os.unlink(db_path)


@pytest.fixture(autouse=True)
def cleanup_database():
    """Clean up database between tests."""
    # Run test
    yield
    # After test, clean up by deleting all records
    with app.app_context():
        db = get_db()
        db.execute('DELETE FROM books')
        db.commit()
        db.close()


def test_health_check(client):
    """Test health check endpoint."""
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


def test_create_book_missing_required_fields(client):
    """Test creating a book without required fields."""
    # Missing title
    book_data = {'author': 'Some Author'}
    response = client.post('/books',
                           data=json.dumps(book_data),
                           content_type='application/json')
    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'error' in data
    
    # Missing author
    book_data = {'title': 'Some Book'}
    response = client.post('/books',
                           data=json.dumps(book_data),
                           content_type='application/json')
    assert response.status_code == 400


def test_create_book_empty_title_author(client):
    """Test creating a book with empty title or author."""
    # Empty title
    book_data = {'title': '', 'author': 'Some Author'}
    response = client.post('/books',
                           data=json.dumps(book_data),
                           content_type='application/json')
    assert response.status_code == 400
    
    # Empty author
    book_data = {'title': 'Some Book', 'author': '   '}
    response = client.post('/books',
                           data=json.dumps(book_data),
                           content_type='application/json')
    assert response.status_code == 400


def test_list_books(client):
    """Test listing books."""
    # Create some books
    client.post('/books', 
                data=json.dumps({'title': 'Book 1', 'author': 'Author A'}),
                content_type='application/json')
    client.post('/books',
                data=json.dumps({'title': 'Book 2', 'author': 'Author B'}),
                content_type='application/json')
    
    response = client.get('/books')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) == 2


def test_list_books_with_author_filter(client):
    """Test listing books with author filter."""
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
    
    # Filter by author (use unique filter to avoid conflicts)
    response = client.get('/books?author=Author+A')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) == 2
    for book in data:
        assert 'Author A' in book['author']


def test_get_book_by_id(client):
    """Test getting a single book by ID."""
    # Create a book
    response = client.post('/books',
                           data=json.dumps({'title': 'Test Book', 'author': 'Test Author'}),
                           content_type='application/json')
    assert response.status_code == 201
    book_id = json.loads(response.data)['id']
    
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


def test_update_book(client):
    """Test updating a book."""
    # Create a book
    response = client.post('/books',
                           data=json.dumps({'title': 'Original Title', 'author': 'Original Author'}),
                           content_type='application/json')
    assert response.status_code == 201
    book_id = json.loads(response.data)['id']
    
    # Update the book
    update_data = {'title': 'Updated Title', 'year': 2024}
    response = client.put(f'/books/{book_id}',
                          data=json.dumps(update_data),
                          content_type='application/json')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['title'] == 'Updated Title'
    assert data['author'] == 'Original Author'  # Unchanged
    assert data['year'] == 2024


def test_update_book_not_found(client):
    """Test updating a non-existent book."""
    update_data = {'title': 'Updated Title'}
    response = client.put('/books/99999',
                          data=json.dumps(update_data),
                          content_type='application/json')
    assert response.status_code == 404


def test_delete_book(client):
    """Test deleting a book."""
    # Create a book
    response = client.post('/books',
                           data=json.dumps({'title': 'To Delete', 'author': 'Author'}),
                           content_type='application/json')
    assert response.status_code == 201
    book_id = json.loads(response.data)['id']
    
    # Delete the book
    response = client.delete(f'/books/{book_id}')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['message'] == 'Book deleted successfully'
    
    # Verify book is gone
    response = client.get(f'/books/{book_id}')
    assert response.status_code == 404


def test_delete_book_not_found(client):
    """Test deleting a non-existent book."""
    response = client.delete('/books/99999')
    assert response.status_code == 404


def test_invalid_book_id(client):
    """Test with invalid book ID."""
    response = client.get('/books/invalid')
    assert response.status_code == 404
    
    response = client.put('/books/invalid',
                          data=json.dumps({'title': 'Test'}),
                          content_type='application/json')
    assert response.status_code == 404
    
    response = client.delete('/books/invalid')
    assert response.status_code == 404


def test_empty_request_body(client):
    """Test endpoints with empty request body."""
    # Test POST with empty body - should fail validation
    response = client.post('/books', data='{}', content_type='application/json')
    assert response.status_code == 400
    
    # Test PUT with empty body on non-existent book - should get 404
    response = client.put('/books/1', data='{}', content_type='application/json')
    # Empty JSON body {} is valid JSON but no data provided
    # The PUT endpoint should check for data presence first
    assert response.status_code == 404


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
