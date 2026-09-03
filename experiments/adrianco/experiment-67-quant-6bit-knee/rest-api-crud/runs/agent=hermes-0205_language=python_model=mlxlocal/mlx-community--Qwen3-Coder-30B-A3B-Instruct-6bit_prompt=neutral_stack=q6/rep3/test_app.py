import pytest
import json
from app import app, init_db

@pytest.fixture
def client():
    """Create a test client for the app."""
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
    # Test valid book creation
    book_data = {
        'title': '1984',
        'author': 'George Orwell',
        'year': 1948,
        'isbn': '978-0-452-28423-4'
    }
    
    response = client.post('/books', 
                          data=json.dumps(book_data),
                          content_type='application/json')
    
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data['title'] == '1984'
    assert data['author'] == 'George Orwell'
    assert data['year'] == 1948
    assert data['isbn'] == '978-0-452-28423-4'
    assert 'id' in data

def test_get_books(client):
    """Test getting all books."""
    # First create a book
    book_data = {
        'title': 'To Kill a Mockingbird',
        'author': 'Harper Lee',
        'year': 1960,
        'isbn': '978-0-06-112008-4'
    }
    
    client.post('/books', 
                data=json.dumps(book_data),
                content_type='application/json')
    
    # Then get all books
    response = client.get('/books')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) >= 1
    
    # Check that our book is in the list
    book_ids = [book['id'] for book in data]
    assert len(book_ids) >= 1

def test_get_book_by_id(client):
    """Test getting a single book by ID."""
    # First create a book
    book_data = {
        'title': 'Pride and Prejudice',
        'author': 'Jane Austen',
        'year': 1813,
        'isbn': '978-0-14-143951-8'
    }
    
    response = client.post('/books', 
                          data=json.dumps(book_data),
                          content_type='application/json')
    assert response.status_code == 201
    book_id = json.loads(response.data)['id']
    
    # Then get the book by ID
    response = client.get(f'/books/{book_id}')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['title'] == 'Pride and Prejudice'
    assert data['author'] == 'Jane Austen'
    assert data['year'] == 1813
    assert data['isbn'] == '978-0-14-143951-8'
    assert data['id'] == book_id

def test_update_book(client):
    """Test updating a book."""
    # First create a book
    book_data = {
        'title': 'The Catcher in the Rye',
        'author': 'J.D. Salinger',
        'year': 1951,
        'isbn': '978-0-316-76948-0'
    }
    
    response = client.post('/books', 
                          data=json.dumps(book_data),
                          content_type='application/json')
    assert response.status_code == 201
    book_id = json.loads(response.data)['id']
    
    # Then update the book
    updated_data = {
        'title': 'The Catcher in the Rye - Updated',
        'author': 'J.D. Salinger',
        'year': 1951,
        'isbn': '978-0-316-76948-0'
    }
    
    response = client.put(f'/books/{book_id}',
                         data=json.dumps(updated_data),
                         content_type='application/json')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['title'] == 'The Catcher in the Rye - Updated'
    assert data['id'] == book_id

def test_delete_book(client):
    """Test deleting a book."""
    # First create a book
    book_data = {
        'title': 'Animal Farm',
        'author': 'George Orwell',
        'year': 1945,
        'isbn': '978-0-452-28423-4'
    }
    
    response = client.post('/books', 
                          data=json.dumps(book_data),
                          content_type='application/json')
    assert response.status_code == 201
    book_id = json.loads(response.data)['id']
    
    # Then delete the book
    response = client.delete(f'/books/{book_id}')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['message'] == 'Book deleted successfully'
    
    # Verify the book is deleted
    response = client.get(f'/books/{book_id}')
    assert response.status_code == 404

def test_create_book_missing_fields(client):
    """Test creating a book with missing required fields."""
    # Test missing title
    book_data = {
        'author': 'George Orwell'
    }
    
    response = client.post('/books', 
                          data=json.dumps(book_data),
                          content_type='application/json')
    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'error' in data

def test_get_nonexistent_book(client):
    """Test getting a book that doesn't exist."""
    response = client.get('/books/999999')
    assert response.status_code == 404
    data = json.loads(response.data)
    assert 'error' in data

def test_update_nonexistent_book(client):
    """Test updating a book that doesn't exist."""
    updated_data = {
        'title': 'Nonexistent Book',
        'author': 'Unknown Author'
    }
    
    response = client.put('/books/999999',
                         data=json.dumps(updated_data),
                         content_type='application/json')
    assert response.status_code == 404
    data = json.loads(response.data)
    assert 'error' in data

def test_delete_nonexistent_book(client):
    """Test deleting a book that doesn't exist."""
    response = client.delete('/books/999999')
    assert response.status_code == 404
    data = json.loads(response.data)
    assert 'error' in data