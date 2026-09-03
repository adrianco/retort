import pytest
import json
from app import app, init_db

@pytest.fixture
def client():
    """Create a test client for the app"""
    app.config['TESTING'] = True
    app.config['DATABASE'] = 'test_books.db'
    
    with app.test_client() as client:
        with app.app_context():
            init_db()
        yield client

def test_health_check(client):
    """Test the health check endpoint"""
    response = client.get('/health')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'healthy'

def test_create_book(client):
    """Test creating a new book"""
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

def test_get_books(client):
    """Test getting all books"""
    # First create a book
    book_data = {
        'title': '1984',
        'author': 'George Orwell',
        'year': 1948,
        'isbn': '978-0-452-28423-4'
    }
    
    client.post('/books', 
                data=json.dumps(book_data),
                content_type='application/json')
    
    # Get all books
    response = client.get('/books')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) >= 1
    
    # Check that our book is in the list
    book_ids = [book['id'] for book in data]
    assert len(book_ids) >= 1

def test_get_book_by_id(client):
    """Test getting a book by ID"""
    # First create a book
    book_data = {
        'title': '1984',
        'author': 'George Orwell',
        'year': 1948,
        'isbn': '978-0-452-28423-4'
    }
    
    response = client.post('/books', 
                          data=json.dumps(book_data),
                          content_type='application/json')
    
    book = json.loads(response.data)
    book_id = book['id']
    
    # Get the book by ID
    response = client.get(f'/books/{book_id}')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['title'] == '1984'
    assert data['author'] == 'George Orwell'

def test_update_book(client):
    """Test updating a book"""
    # First create a book
    book_data = {
        'title': '1984',
        'author': 'George Orwell',
        'year': 1948,
        'isbn': '978-0-452-28423-4'
    }
    
    response = client.post('/books', 
                          data=json.dumps(book_data),
                          content_type='application/json')
    
    book = json.loads(response.data)
    book_id = book['id']
    
    # Update the book
    updated_data = {
        'title': 'Nineteen Eighty-Four',
        'author': 'George Orwell',
        'year': 1948,
        'isbn': '978-0-452-28423-4'
    }
    
    response = client.put(f'/books/{book_id}',
                         data=json.dumps(updated_data),
                         content_type='application/json')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['title'] == 'Nineteen Eighty-Four'

def test_delete_book(client):
    """Test deleting a book"""
    # First create a book
    book_data = {
        'title': '1984',
        'author': 'George Orwell',
        'year': 1948,
        'isbn': '978-0-452-28423-4'
    }
    
    response = client.post('/books', 
                          data=json.dumps(book_data),
                          content_type='application/json')
    
    book = json.loads(response.data)
    book_id = book['id']
    
    # Delete the book
    response = client.delete(f'/books/{book_id}')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['message'] == 'Book deleted successfully'

def test_create_book_missing_fields(client):
    """Test creating a book with missing required fields"""
    # Test with missing title
    book_data = {
        'author': 'George Orwell',
        'year': 1948
    }
    
    response = client.post('/books', 
                          data=json.dumps(book_data),
                          content_type='application/json')
    
    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'error' in data

def test_get_nonexistent_book(client):
    """Test getting a book that doesn't exist"""
    response = client.get('/books/999')
    assert response.status_code == 404
    data = json.loads(response.data)
    assert 'error' in data

def test_filter_books_by_author(client):
    """Test filtering books by author"""
    # Create two books with different authors
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
    
    client.post('/books', 
                data=json.dumps(book1_data),
                content_type='application/json')
    
    client.post('/books', 
                data=json.dumps(book2_data),
                content_type='application/json')
    
    # Filter by author
    response = client.get('/books?author=Orwell')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) >= 2
    
    # Check that all returned books have the author 'George Orwell'
    for book in data:
        assert book['author'] == 'George Orwell'