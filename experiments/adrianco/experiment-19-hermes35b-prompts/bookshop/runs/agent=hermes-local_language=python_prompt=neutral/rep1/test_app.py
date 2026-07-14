import pytest
import os
import json

from app import app, db, Book, init_db


@pytest.fixture
def client():
    """Create a test client with a fresh in-memory database."""
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['TESTING'] = True

    with app.test_client() as client:
        with app.app_context():
            db.drop_all()
            db.create_all()
        yield client


@pytest.fixture
def sample_book():
    """Provide a sample book for testing."""
    return {
        'title': 'The Great Gatsby',
        'author': 'F. Scott Fitzgerald',
        'year': 1925,
        'isbn': '978-0743273565'
    }


def test_health_check(client):
    """Test that the health check endpoint returns healthy status."""
    response = client.get('/health')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'healthy'


def test_create_book(client, sample_book):
    """Test creating a new book."""
    response = client.post('/books',
                           data=json.dumps(sample_book),
                           content_type='application/json')
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data['title'] == 'The Great Gatsby'
    assert data['author'] == 'F. Scott Fitzgerald'
    assert data['year'] == 1925
    assert data['isbn'] == '978-0743273565'
    assert 'id' in data


def test_create_book_missing_title(client):
    """Test that creating a book without title returns 400."""
    response = client.post('/books',
                           data=json.dumps({'author': 'Test Author'}),
                           content_type='application/json')
    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'error' in data


def test_create_book_missing_author(client):
    """Test that creating a book without author returns 400."""
    response = client.post('/books',
                           data=json.dumps({'title': 'Test Book'}),
                           content_type='application/json')
    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'error' in data


def test_list_books_empty(client):
    """Test listing books when the collection is empty."""
    response = client.get('/books')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data == []


def test_list_books_with_data(client, sample_book):
    """Test listing books when there are entries."""
    client.post('/books',
                data=json.dumps(sample_book),
                content_type='application/json')
    response = client.get('/books')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) == 1


def test_filter_books_by_author(client):
    """Test filtering books by author."""
    book1 = {
        'title': 'Book One',
        'author': 'John Doe',
        'year': 2020,
        'isbn': '111'
    }
    book2 = {
        'title': 'Book Two',
        'author': 'Jane Smith',
        'year': 2021,
        'isbn': '222'
    }
    client.post('/books', data=json.dumps(book1),
                content_type='application/json')
    client.post('/books', data=json.dumps(book2),
                content_type='application/json')

    response = client.get('/books?author=John+Doe')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) == 1
    assert data[0]['author'] == 'John Doe'


def test_get_single_book(client, sample_book):
    """Test getting a single book by ID."""
    response = client.post('/books',
                           data=json.dumps(sample_book),
                           content_type='application/json')
    book_data = json.loads(response.data)
    book_id = book_data['id']

    response = client.get(f'/books/{book_id}')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['title'] == 'The Great Gatsby'


def test_get_book_not_found(client):
    """Test getting a non-existent book returns 404."""
    response = client.get('/books/999')
    assert response.status_code == 404


def test_update_book(client, sample_book):
    """Test updating an existing book."""
    # Create first
    response = client.post('/books',
                           data=json.dumps(sample_book),
                           content_type='application/json')
    book_data = json.loads(response.data)
    book_id = book_data['id']

    # Update
    update_data = {'title': 'Updated Title', 'year': 2024}
    response = client.put(f'/books/{book_id}',
                          data=json.dumps(update_data),
                          content_type='application/json')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['title'] == 'Updated Title'
    assert data['year'] == 2024
    assert data['author'] == 'F. Scott Fitzgerald'  # unchanged


def test_update_book_not_found(client):
    """Test updating a non-existent book returns 404."""
    response = client.put('/books/999',
                          data=json.dumps({'title': 'New Title'}),
                          content_type='application/json')
    assert response.status_code == 404


def test_delete_book(client, sample_book):
    """Test deleting a book."""
    # Create first
    response = client.post('/books',
                           data=json.dumps(sample_book),
                           content_type='application/json')
    book_data = json.loads(response.data)
    book_id = book_data['id']

    # Delete
    response = client.delete(f'/books/{book_id}')
    assert response.status_code == 200

    # Verify it's gone
    response = client.get(f'/books/{book_id}')
    assert response.status_code == 404


def test_delete_book_not_found(client):
    """Test deleting a non-existent book returns 404."""
    response = client.delete('/books/999')
    assert response.status_code == 404


def test_invalid_year(client):
    """Test that non-integer year returns 400."""
    book = {
        'title': 'Bad Year Book',
        'author': 'Test Author',
        'year': 'not a year'
    }
    response = client.post('/books',
                           data=json.dumps(book),
                           content_type='application/json')
    assert response.status_code == 400
