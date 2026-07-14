"""
Integration tests for the Book Collection REST API
"""
import pytest
import os
import json
import sqlite3

# Set test database before importing app
os.environ['DATABASE'] = 'test_books.db'


@pytest.fixture
def client():
    """Create a test client with test database."""
    # Clean up test database first
    if os.path.exists('test_books.db'):
        os.remove('test_books.db')
    
    # Import app after setting DATABASE env var
    from app import app, init_db
    
    # Initialize test database
    init_db()
    
    # Configure for testing
    app.config['TESTING'] = True
    
    # Create test client
    with app.test_client() as client:
        yield client
    
    # Clean up test database
    if os.path.exists('test_books.db'):
        os.remove('test_books.db')


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


def test_create_book_validation(client):
    """Test book creation validation."""
    # Missing title
    response = client.post('/books',
                           data=json.dumps({'author': 'Test Author'}),
                           content_type='application/json')
    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'error' in data
    assert 'Title is required' in data['error']
    
    # Missing author
    response = client.post('/books',
                           data=json.dumps({'title': 'Test Title'}),
                           content_type='application/json')
    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'Author is required' in data['error']


def test_create_book_with_optional_fields(client):
    """Test creating a book with optional fields."""
    book_data = {
        'title': '1984',
        'author': 'George Orwell',
        'year': 1949,
        'isbn': '978-0451524935'
    }
    
    response = client.post('/books',
                           data=json.dumps(book_data),
                           content_type='application/json')
    
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data['title'] == '1984'
    assert data['author'] == 'George Orwell'
    assert data['year'] == 1949
    assert data['isbn'] == '978-0451524935'


def test_list_books(client):
    """Test listing books."""
    # Create a book first
    client.post('/books',
                data=json.dumps({
                    'title': 'Test Book 1',
                    'author': 'Author A'
                }),
                content_type='application/json')
    
    client.post('/books',
                data=json.dumps({
                    'title': 'Test Book 2',
                    'author': 'Author B'
                }),
                content_type='application/json')
    
    response = client.get('/books')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert isinstance(data, list)
    assert len(data) == 2


def test_list_books_with_author_filter(client):
    """Test listing books with author filter."""
    # Create books with different authors
    client.post('/books',
                data=json.dumps({
                    'title': 'Book 1',
                    'author': 'John Doe'
                }),
                content_type='application/json')
    
    client.post('/books',
                data=json.dumps({
                    'title': 'Book 2',
                    'author': 'Jane Smith'
                }),
                content_type='application/json')
    
    # Filter by author
    response = client.get('/books?author=John')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) == 1
    assert data[0]['author'] == 'John Doe'


def test_get_book(client):
    """Test getting a single book."""
    # Create a book
    create_response = client.post('/books',
                                  data=json.dumps({
                                      'title': 'Test Book',
                                      'author': 'Test Author'
                                  }),
                                  content_type='application/json')
    
    book_id = json.loads(create_response.data)['id']
    
    # Get the book
    response = client.get(f'/books/{book_id}')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['id'] == book_id
    assert data['title'] == 'Test Book'
    assert data['author'] == 'Test Author'


def test_get_book_not_found(client):
    """Test getting a non-existent book."""
    response = client.get('/books/9999')
    assert response.status_code == 404
    data = json.loads(response.data)
    assert 'error' in data


def test_update_book(client):
    """Test updating a book."""
    # Create a book
    create_response = client.post('/books',
                                  data=json.dumps({
                                      'title': 'Original Title',
                                      'author': 'Original Author'
                                  }),
                                  content_type='application/json')
    
    book_id = json.loads(create_response.data)['id']
    
    # Update the book
    update_data = {
        'title': 'Updated Title',
        'author': 'Updated Author',
        'year': 2024
    }
    
    response = client.put(f'/books/{book_id}',
                          data=json.dumps(update_data),
                          content_type='application/json')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['title'] == 'Updated Title'
    assert data['author'] == 'Updated Author'
    assert data['year'] == 2024


def test_update_book_partial(client):
    """Test updating only some fields of a book."""
    # Create a book
    create_response = client.post('/books',
                                  data=json.dumps({
                                      'title': 'Original Title',
                                      'author': 'Original Author',
                                      'year': 2020
                                  }),
                                  content_type='application/json')
    
    book_id = json.loads(create_response.data)['id']
    
    # Update only the title
    update_data = {
        'title': 'Partially Updated Title'
    }
    
    response = client.put(f'/books/{book_id}',
                          data=json.dumps(update_data),
                          content_type='application/json')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['title'] == 'Partially Updated Title'
    assert data['author'] == 'Original Author'
    assert data['year'] == 2020


def test_update_book_not_found(client):
    """Test updating a non-existent book."""
    update_data = {
        'title': 'Updated Title'
    }
    
    response = client.put('/books/9999',
                          data=json.dumps(update_data),
                          content_type='application/json')
    
    assert response.status_code == 404


def test_delete_book(client):
    """Test deleting a book."""
    # Create a book
    create_response = client.post('/books',
                                  data=json.dumps({
                                      'title': 'To Delete',
                                      'author': 'Delete Author'
                                  }),
                                  content_type='application/json')
    
    book_id = json.loads(create_response.data)['id']
    
    # Delete the book
    response = client.delete(f'/books/{book_id}')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['message'] == 'Book deleted successfully'
    
    # Verify book is deleted
    get_response = client.get(f'/books/{book_id}')
    assert get_response.status_code == 404


def test_delete_book_not_found(client):
    """Test deleting a non-existent book."""
    response = client.delete('/books/9999')
    assert response.status_code == 404
    data = json.loads(response.data)
    assert 'error' in data


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
