import pytest
import json
from app import app, init_db

@pytest.fixture
def client():
    """Create a test client"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        # Initialize database for tests
        init_db()
        yield client

def test_health_check(client):
    """Test health check endpoint"""
    response = client.get('/health')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'healthy'

def test_create_book(client):
    """Test creating a new book"""
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
    """Test creating a book with missing required fields"""
    book_data = {
        'title': 'Test Book'
        # Missing author
    }
    
    response = client.post('/books', 
                          data=json.dumps(book_data),
                          content_type='application/json')
    
    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'error' in data

def test_get_books(client):
    """Test getting all books"""
    # First create a book
    book_data = {
        'title': 'Test Book',
        'author': 'Test Author',
        'year': 2023
    }
    
    client.post('/books', 
                data=json.dumps(book_data),
                content_type='application/json')
    
    # Get all books
    response = client.get('/books')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) >= 1

def test_get_books_by_author(client):
    """Test getting books filtered by author"""
    # First create a book
    book_data = {
        'title': 'Test Book',
        'author': 'Test Author',
        'year': 2023
    }
    
    client.post('/books', 
                data=json.dumps(book_data),
                content_type='application/json')
    
    # Get books by author
    response = client.get('/books?author=Test Author')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) >= 1
    assert data[0]['author'] == 'Test Author'

def test_get_single_book(client):
    """Test getting a single book by ID"""
    # First create a book
    book_data = {
        'title': 'Test Book',
        'author': 'Test Author',
        'year': 2023
    }
    
    response = client.post('/books', 
                          data=json.dumps(book_data),
                          content_type='application/json')
    
    # Get the created book by ID
    book_id = json.loads(response.data)['id']
    response = client.get(f'/books/{book_id}')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['title'] == 'Test Book'
    assert data['author'] == 'Test Author'

def test_update_book(client):
    """Test updating a book"""
    # First create a book
    book_data = {
        'title': 'Test Book',
        'author': 'Test Author',
        'year': 2023
    }
    
    response = client.post('/books', 
                          data=json.dumps(book_data),
                          content_type='application/json')
    
    book_id = json.loads(response.data)['id']
    
    # Update the book
    update_data = {
        'title': 'Updated Test Book',
        'author': 'Updated Test Author',
        'year': 2024,
        'isbn': '0987654321'
    }
    
    response = client.put(f'/books/{book_id}',
                         data=json.dumps(update_data),
                         content_type='application/json')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['title'] == 'Updated Test Book'
    assert data['author'] == 'Updated Test Author'
    assert data['year'] == 2024
    assert data['isbn'] == '0987654321'

def test_delete_book(client):
    """Test deleting a book"""
    # First create a book
    book_data = {
        'title': 'Test Book',
        'author': 'Test Author',
        'year': 2023
    }
    
    response = client.post('/books', 
                          data=json.dumps(book_data),
                          content_type='application/json')
    
    book_id = json.loads(response.data)['id']
    
    # Delete the book
    response = client.delete(f'/books/{book_id}')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['message'] == 'Book deleted successfully'

def test_book_not_found(client):
    """Test accessing a non-existent book"""
    response = client.get('/books/99999')
    assert response.status_code == 404
    data = json.loads(response.data)
    assert 'error' in data

def test_update_nonexistent_book(client):
    """Test updating a non-existent book"""
    update_data = {
        'title': 'Updated Test Book',
        'author': 'Updated Test Author'
    }
    
    response = client.put('/books/99999',
                         data=json.dumps(update_data),
                         content_type='application/json')
    
    assert response.status_code == 404
    data = json.loads(response.data)
    assert 'error' in data

def test_delete_nonexistent_book(client):
    """Test deleting a non-existent book"""
    response = client.delete('/books/99999')
    assert response.status_code == 404
    data = json.loads(response.data)
    assert 'error' in data