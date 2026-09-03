import pytest
import json
from app import app, init_db

@pytest.fixture
def client():
    """Create a test client for the Flask app."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        # Initialize database before each test
        init_db()
        yield client

def test_health_check(client):
    """Test the health check endpoint."""
    response = client.get('/health')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'healthy'

def test_create_book(client):
    """Test creating a new book."""
    book_data = {
        'title': 'Test Book',
        'author': 'Test Author',
        'year': 2023,
        'isbn': '1234567890'
    }
    
    response = client.post('/books', 
                          data=json.dumps(book_data),
                          content_type='application/json')
    
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data['title'] == 'Test Book'
    assert data['author'] == 'Test Author'
    assert data['year'] == 2023
    assert data['isbn'] == '1234567890'

def test_create_book_missing_fields(client):
    """Test creating a book with missing required fields."""
    book_data = {
        'title': 'Test Book'
        # Missing author field
    }
    
    response = client.post('/books', 
                          data=json.dumps(book_data),
                          content_type='application/json')
    
    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'error' in data

def test_get_books(client):
    """Test retrieving all books."""
    # First create a book
    book_data = {
        'title': 'Test Book',
        'author': 'Test Author',
        'year': 2023,
        'isbn': '1234567890'
    }
    
    client.post('/books', 
                data=json.dumps(book_data),
                content_type='application/json')
    
    # Then get all books
    response = client.get('/books')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) >= 1

def test_get_book_by_id(client):
    """Test retrieving a single book by ID."""
    # First create a book
    book_data = {
        'title': 'Test Book',
        'author': 'Test Author',
        'year': 2023,
        'isbn': '1234567890'
    }
    
    response = client.post('/books', 
                          data=json.dumps(book_data),
                          content_type='application/json')
    book_id = json.loads(response.data)['id']
    
    # Then get the book by ID
    response = client.get(f'/books/{book_id}')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['title'] == 'Test Book'
    assert data['author'] == 'Test Author'

def test_update_book(client):
    """Test updating a book."""
    # First create a book
    book_data = {
        'title': 'Test Book',
        'author': 'Test Author',
        'year': 2023,
        'isbn': '1234567890'
    }
    
    response = client.post('/books', 
                          data=json.dumps(book_data),
                          content_type='application/json')
    book_id = json.loads(response.data)['id']
    
    # Then update the book
    updated_data = {
        'title': 'Updated Test Book',
        'author': 'Updated Test Author',
        'year': 2024,
        'isbn': '0987654321'
    }
    
    response = client.put(f'/books/{book_id}',
                         data=json.dumps(updated_data),
                         content_type='application/json')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['title'] == 'Updated Test Book'
    assert data['author'] == 'Updated Test Author'
    assert data['year'] == 2024
    assert data['isbn'] == '0987654321'

def test_delete_book(client):
    """Test deleting a book."""
    # First create a book
    book_data = {
        'title': 'Test Book',
        'author': 'Test Author',
        'year': 2023,
        'isbn': '1234567890'
    }
    
    response = client.post('/books', 
                          data=json.dumps(book_data),
                          content_type='application/json')
    book_id = json.loads(response.data)['id']
    
    # Then delete the book
    response = client.delete(f'/books/{book_id}')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['message'] == 'Book deleted successfully'

def test_get_nonexistent_book(client):
    """Test retrieving a non-existent book."""
    response = client.get('/books/99999')
    assert response.status_code == 404
    data = json.loads(response.data)
    assert 'error' in data

def test_update_nonexistent_book(client):
    """Test updating a non-existent book."""
    updated_data = {
        'title': 'Updated Test Book',
        'author': 'Updated Test Author'
    }
    
    response = client.put('/books/99999',
                         data=json.dumps(updated_data),
                         content_type='application/json')
    
    assert response.status_code == 404
    data = json.loads(response.data)
    assert 'error' in data

def test_delete_nonexistent_book(client):
    """Test deleting a non-existent book."""
    response = client.delete('/books/99999')
    assert response.status_code == 404
    data = json.loads(response.data)
    assert 'error' in data