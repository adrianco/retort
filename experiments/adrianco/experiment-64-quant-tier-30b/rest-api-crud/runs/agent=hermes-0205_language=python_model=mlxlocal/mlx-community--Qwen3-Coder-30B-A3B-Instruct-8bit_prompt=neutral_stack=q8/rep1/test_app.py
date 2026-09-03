import pytest
import json
import tempfile
import os
import sys

# Add current directory to path so we can import app properly
sys.path.insert(0, '.')

# Import the app after path fix
from app import app, init_db

@pytest.fixture
def client():
    """Create a test client for the app with isolated database"""
    # Create a temporary database for testing
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    
    # Create a new app instance with the test database
    test_app = app
    test_app.config['TESTING'] = True
    test_app.config['DATABASE'] = db_path
    
    # Initialize database for this instance
    with test_app.app_context():
        init_db()
    
    with test_app.test_client() as client:
        yield client
    
    # Clean up the temporary database
    os.close(db_fd)
    os.unlink(db_path)

def test_health_check(client):
    """Test the health check endpoint"""
    response = client.get('/health')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'healthy'

def test_create_book(client):
    """Test creating a new book"""
    book_data = {
        'title': '1984',
        'author': 'George Orwell',
        'year': 1948,
        'isbn': '978-0451524935'
    }
    
    response = client.post('/books', 
                          data=json.dumps(book_data),
                          content_type='application/json')
    
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data['title'] == '1984'
    assert data['author'] == 'George Orwell'
    assert data['year'] == 1948
    assert data['isbn'] == '978-0451524935'

def test_create_book_missing_fields(client):
    """Test creating a book with missing required fields"""
    book_data = {
        'title': '1984'
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
        'title': '1984',
        'author': 'George Orwell',
        'year': 1948
    }
    
    client.post('/books', 
                data=json.dumps(book_data),
                content_type='application/json')
    
    # Get all books
    response = client.get('/books')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) == 1
    assert data[0]['title'] == '1984'

def test_get_books_by_author(client):
    """Test getting books filtered by author"""
    # Create books
    book1_data = {
        'title': '1984',
        'author': 'George Orwell',
        'year': 1948
    }
    
    book2_data = {
        'title': 'Animal Farm',
        'author': 'George Orwell',
        'year': 1945
    }
    
    book3_data = {
        'title': 'To Kill a Mockingbird',
        'author': 'Harper Lee',
        'year': 1960
    }
    
    client.post('/books', 
                data=json.dumps(book1_data),
                content_type='application/json')
    
    client.post('/books', 
                data=json.dumps(book2_data),
                content_type='application/json')
    
    client.post('/books', 
                data=json.dumps(book3_data),
                content_type='application/json')
    
    # Filter by author
    response = client.get('/books?author=Orwell')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) == 2
    assert all(book['author'] == 'George Orwell' for book in data)

def test_get_single_book(client):
    """Test getting a single book by ID"""
    # Create a book
    book_data = {
        'title': '1984',
        'author': 'George Orwell',
        'year': 1948
    }
    
    response = client.post('/books', 
                          data=json.dumps(book_data),
                          content_type='application/json')
    
    book_id = json.loads(response.data)['id']
    
    # Get the book by ID
    response = client.get(f'/books/{book_id}')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['title'] == '1984'
    assert data['author'] == 'George Orwell'
    assert data['year'] == 1948

def test_update_book(client):
    """Test updating a book"""
    # Create a book
    book_data = {
        'title': '1984',
        'author': 'George Orwell',
        'year': 1948
    }
    
    response = client.post('/books', 
                          data=json.dumps(book_data),
                          content_type='application/json')
    
    book_id = json.loads(response.data)['id']
    
    # Update the book
    updated_data = {
        'title': 'Nineteen Eighty-Four',
        'author': 'George Orwell',
        'year': 1948,
        'isbn': '978-0451524935'
    }
    
    response = client.put(f'/books/{book_id}',
                         data=json.dumps(updated_data),
                         content_type='application/json')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['title'] == 'Nineteen Eighty-Four'
    assert data['isbn'] == '978-0451524935'

def test_delete_book(client):
    """Test deleting a book"""
    # Create a book
    book_data = {
        'title': '1984',
        'author': 'George Orwell',
        'year': 1948
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
    
    # Verify it's deleted
    response = client.get(f'/books/{book_id}')
    assert response.status_code == 404

def test_book_not_found(client):
    """Test accessing a non-existent book"""
    response = client.get('/books/999')
    assert response.status_code == 404
    data = json.loads(response.data)
    assert 'error' in data