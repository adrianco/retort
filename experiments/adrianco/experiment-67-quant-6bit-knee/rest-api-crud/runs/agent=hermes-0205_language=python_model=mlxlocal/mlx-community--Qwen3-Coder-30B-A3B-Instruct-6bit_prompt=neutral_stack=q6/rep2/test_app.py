import pytest
import json
import tempfile
import os
from app import app, init_db

@pytest.fixture
def client():
    """Create a test client for the Flask app."""
    # Create a temporary database file for testing
    db_fd, db_path = tempfile.mkstemp()
    
    # Set the database path in the environment
    original_db = os.environ.get('DATABASE')
    os.environ['DATABASE'] = db_path
    
    app.config['TESTING'] = True
    
    with app.test_client() as client:
        with app.app_context():
            init_db()
        yield client
    
    # Restore original environment variable and clean up
    if original_db is not None:
        os.environ['DATABASE'] = original_db
    else:
        os.environ.pop('DATABASE', None)
    
    os.close(db_fd)
    os.unlink(db_path)

def test_health_check(client):
    """Test the health check endpoint."""
    response = client.get('/health')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'healthy'

def test_create_book_success(client):
    """Test creating a book with valid data."""
    response = client.post('/books',
        data=json.dumps({
            'title': '1984',
            'author': 'George Orwell',
            'year': 1948,
            'isbn': '978-0451524935'
        }),
        content_type='application/json'
    )
    
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data['title'] == '1984'
    assert data['author'] == 'George Orwell'
    assert data['year'] == 1948
    assert data['isbn'] == '978-0451524935'
    assert 'id' in data

def test_create_book_missing_fields(client):
    """Test creating a book with missing required fields."""
    response = client.post('/books',
        data=json.dumps({
            'title': '1984'
            # Missing author
        }),
        content_type='application/json'
    )
    
    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'error' in data

def test_create_book_empty_fields(client):
    """Test creating a book with empty title or author."""
    response = client.post('/books',
        data=json.dumps({
            'title': '',
            'author': 'George Orwell'
        }),
        content_type='application/json'
    )
    
    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'error' in data

def test_get_all_books_empty(client):
    """Test getting all books when the database is empty."""
    response = client.get('/books')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data == []

def test_get_all_books_with_data(client):
    """Test getting all books with some data."""
    # First create a book
    client.post('/books',
        data=json.dumps({
            'title': '1984',
            'author': 'George Orwell',
            'year': 1948
        }),
        content_type='application/json'
    )
    
    # Then get all books
    response = client.get('/books')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) == 1
    assert data[0]['title'] == '1984'
    assert data[0]['author'] == 'George Orwell'

def test_get_books_by_author(client):
    """Test getting books filtered by author."""
    # Create two books
    client.post('/books',
        data=json.dumps({
            'title': '1984',
            'author': 'George Orwell',
            'year': 1948
        }),
        content_type='application/json'
    )
    
    client.post('/books',
        data=json.dumps({
            'title': 'Animal Farm',
            'author': 'George Orwell',
            'year': 1945
        }),
        content_type='application/json'
    )
    
    client.post('/books',
        data=json.dumps({
            'title': 'To Kill a Mockingbird',
            'author': 'Harper Lee',
            'year': 1960
        }),
        content_type='application/json'
    )
    
    # Get books by author
    response = client.get('/books?author=Orwell')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) == 2
    for book in data:
        assert book['author'] == 'George Orwell'

def test_get_book_by_id_success(client):
    """Test getting a book by valid ID."""
    # First create a book
    create_response = client.post('/books',
        data=json.dumps({
            'title': '1984',
            'author': 'George Orwell',
            'year': 1948
        }),
        content_type='application/json'
    )
    
    book_data = json.loads(create_response.data)
    book_id = book_data['id']
    
    # Then get the book by ID
    response = client.get(f'/books/{book_id}')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['title'] == '1984'
    assert data['author'] == 'George Orwell'
    assert data['id'] == book_id

def test_get_book_by_id_not_found(client):
    """Test getting a book by non-existent ID."""
    response = client.get('/books/999')
    assert response.status_code == 404
    data = json.loads(response.data)
    assert 'error' in data

def test_update_book_success(client):
    """Test updating a book with valid data."""
    # First create a book
    create_response = client.post('/books',
        data=json.dumps({
            'title': '1984',
            'author': 'George Orwell',
            'year': 1948
        }),
        content_type='application/json'
    )
    
    book_data = json.loads(create_response.data)
    book_id = book_data['id']
    
    # Then update the book
    response = client.put(f'/books/{book_id}',
        data=json.dumps({
            'title': 'Nineteen Eighty-Four',
            'author': 'George Orwell',
            'year': 1948,
            'isbn': '978-0451524935'
        }),
        content_type='application/json'
    )
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['title'] == 'Nineteen Eighty-Four'
    assert data['author'] == 'George Orwell'
    assert data['year'] == 1948
    assert data['isbn'] == '978-0451524935'

def test_update_book_not_found(client):
    """Test updating a non-existent book."""
    response = client.put('/books/999',
        data=json.dumps({
            'title': '1984',
            'author': 'George Orwell'
        }),
        content_type='application/json'
    )
    
    assert response.status_code == 404
    data = json.loads(response.data)
    assert 'error' in data

def test_update_book_empty_fields(client):
    """Test updating a book with empty title or author."""
    # First create a book
    create_response = client.post('/books',
        data=json.dumps({
            'title': '1984',
            'author': 'George Orwell'
        }),
        content_type='application/json'
    )
    
    book_data = json.loads(create_response.data)
    book_id = book_data['id']
    
    # Then try to update with empty fields
    response = client.put(f'/books/{book_id}',
        data=json.dumps({
            'title': '',
            'author': 'George Orwell'
        }),
        content_type='application/json'
    )
    
    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'error' in data

def test_delete_book_success(client):
    """Test deleting a book with valid ID."""
    # First create a book
    create_response = client.post('/books',
        data=json.dumps({
            'title': '1984',
            'author': 'George Orwell'
        }),
        content_type='application/json'
    )
    
    book_data = json.loads(create_response.data)
    book_id = book_data['id']
    
    # Then delete the book
    response = client.delete(f'/books/{book_id}')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'message' in data

def test_delete_book_not_found(client):
    """Test deleting a non-existent book."""
    response = client.delete('/books/999')
    assert response.status_code == 404
    data = json.loads(response.data)
    assert 'error' in data

if __name__ == '__main__':
    pytest.main([__file__, '-v'])