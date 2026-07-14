
import pytest
import json
from app import app, init_db
import sqlite3

DATABASE = 'books.db'

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        with app.app_context():
            init_db()
        yield client
        with app.app_context():
            # Clean up the database after tests
            conn = sqlite3.connect(DATABASE)
            conn.execute('DROP TABLE IF EXISTS books')
            conn.commit()
            conn.close()

def test_create_book(client):
    response = client.post('/books', json={
        'title': 'Test Book',
        'author': 'Test Author',
        'year': 2023,
        'isbn': '1234567890'
    })
    assert response.status_code == 201
    data = response.get_json()
    assert 'id' in data
    assert data['title'] == 'Test Book'
    assert data['author'] == 'Test Author'

def test_list_books(client):
    # Create a book first
    client.post('/books', json={
        'title': 'Test Book',
        'author': 'Test Author',
        'year': 2023,
        'isbn': '1234567890'
    })
    
    response = client.get('/books')
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 1
    assert data[0]['title'] == 'Test Book'

def test_get_book(client):
    # Create a book first
    response = client.post('/books', json={
        'title': 'Test Book',
        'author': 'Test Author',
        'year': 2023,
        'isbn': '1234567890'
    })
    book_id = response.get_json()['id']
    
    response = client.get(f'/books/{book_id}')
    assert response.status_code == 200
    data = response.get_json()
    assert data['title'] == 'Test Book'
    assert data['author'] == 'Test Author'

def test_update_book(client):
    # Create a book first
    response = client.post('/books', json={
        'title': 'Test Book',
        'author': 'Test Author',
        'year': 2023,
        'isbn': '1234567890'
    })
    book_id = response.get_json()['id']
    
    response = client.put(f'/books/{book_id}', json={
        'title': 'Updated Book',
        'author': 'Updated Author',
        'year': 2024,
        'isbn': '0987654321'
    })
    assert response.status_code == 200
    data = response.get_json()
    assert data['title'] == 'Updated Book'
    assert data['author'] == 'Updated Author'

def test_delete_book(client):
    # Create a book first
    response = client.post('/books', json={
        'title': 'Test Book',
        'author': 'Test Author',
        'year': 2023,
        'isbn': '1234567890'
    })
    book_id = response.get_json()['id']
    
    response = client.delete(f'/books/{book_id}')
    assert response.status_code == 204


def test_health_check(client):
    response = client.get('/health')
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'OK'

def test_validation(client):
    # Test missing title
    response = client.post('/books', json={
        'author': 'Test Author',
        'year': 2023,
        'isbn': '1234567890'
    })
    assert response.status_code == 400
    
    # Test missing author
    response = client.post('/books', json={
        'title': 'Test Book',
        'year': 2023,
        'isbn': '1234567890'
    })
    assert response.status_code == 400

def test_filter_by_author(client):
    # Create two books with different authors
    client.post('/books', json={
        'title': 'Book 1',
        'author': 'Author 1',
        'year': 2023,
        'isbn': '1234567890'
    })
    client.post('/books', json={
        'title': 'Book 2',
        'author': 'Author 2',
        'year': 2023,
        'isbn': '0987654321'
    })
    
    # Filter by author
    response = client.get('/books?author=Author 1')
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 1
    assert data[0]['author'] == 'Author 1'
