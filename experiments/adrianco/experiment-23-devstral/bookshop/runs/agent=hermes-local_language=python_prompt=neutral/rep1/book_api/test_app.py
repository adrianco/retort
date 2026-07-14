import pytest
import json
import sqlite3
from app import app, init_db, get_db

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        # Initialize test database
        init_db()
        yield client
        # Clean up test database
        with get_db() as db:
            db.execute('DELETE FROM books')
            db.commit()

def test_health_check(client):
    response = client.get('/health')
    assert response.status_code == 200
    assert json.loads(response.data) == {'status': 'healthy'}

def test_create_book(client):
    book = {
        'title': 'To Kill a Mockingbird',
        'author': 'Harper Lee',
        'year': 1960,
        'isbn': '9780061120084'
    }
    response = client.post('/books', json=book)
    assert response.status_code == 201
    data = json.loads(response.data)
    assert 'id' in data
    assert data['title'] == book['title']
    assert data['author'] == book['author']

def test_create_book_missing_required_field(client):
    book = {
        'title': 'To Kill a Mockingbird',
        # Missing author
        'year': 1960,
        'isbn': '9780061120084'
    }
    response = client.post('/books', json=book)
    assert response.status_code == 400
    assert 'error' in json.loads(response.data)

def test_list_books(client):
    # Add a book first
    book = {
        'title': 'To Kill a Mockingbird',
        'author': 'Harper Lee',
        'year': 1960,
        'isbn': '9780061120084'
    }
    client.post('/books', json=book)
    
    response = client.get('/books')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) == 1
    assert data[0]['title'] == book['title']

def test_list_books_with_author_filter(client):
    # Add books from different authors
    book1 = {
        'title': 'To Kill a Mockingbird',
        'author': 'Harper Lee',
        'year': 1960,
        'isbn': '9780061120084'
    }
    book2 = {
        'title': '1984',
        'author': 'George Orwell',
        'year': 1949,
        'isbn': '9780451524935'
    }
    client.post('/books', json=book1)
    client.post('/books', json=book2)
    
    response = client.get('/books?author=Harper%20Lee')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) == 1
    assert data[0]['author'] == 'Harper Lee'

def test_get_book(client):
    # Add a book first
    book = {
        'title': 'To Kill a Mockingbird',
        'author': 'Harper Lee',
        'year': 1960,
        'isbn': '9780061120084'
    }
    response = client.post('/books', json=book)
    data = json.loads(response.data)
    book_id = data['id']
    
    response = client.get(f'/books/{book_id}')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['title'] == book['title']
    assert data['author'] == book['author']

def test_get_book_not_found(client):
    response = client.get('/books/99999')
    assert response.status_code == 404

def test_update_book(client):
    # Add a book first
    book = {
        'title': 'To Kill a Mockingbird',
        'author': 'Harper Lee',
        'year': 1960,
        'isbn': '9780061120084'
    }
    response = client.post('/books', json=book)
    data = json.loads(response.data)
    book_id = data['id']
    
    # Update the book
    updated_book = {
        'title': 'To Kill a Mockingbird (Updated)',
        'author': 'Harper Lee',
        'year': 1961,  # Updated year
        'isbn': '9780061120084'
    }
    response = client.put(f'/books/{book_id}', json=updated_book)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['title'] == updated_book['title']
    assert data['year'] == updated_book['year']

def test_update_book_missing_required_field(client):
    # Add a book first
    book = {
        'title': 'To Kill a Mockingbird',
        'author': 'Harper Lee',
        'year': 1960,
        'isbn': '9780061120084'
    }
    response = client.post('/books', json=book)
    data = json.loads(response.data)
    book_id = data['id']
    
    # Try to update without required fields
    updated_book = {
        'title': 'To Kill a Mockingbird (Updated)',
        # Missing author
        'year': 1961,
        'isbn': '9780061120084'
    }
    response = client.put(f'/books/{book_id}', json=updated_book)
    assert response.status_code == 400

def test_delete_book(client):
    # Add a book first
    book = {
        'title': 'To Kill a Mockingbird',
        'author': 'Harper Lee',
        'year': 1960,
        'isbn': '9780061120084'
    }
    response = client.post('/books', json=book)
    data = json.loads(response.data)
    book_id = data['id']
    
    # Delete the book
    response = client.delete(f'/books/{book_id}')
    assert response.status_code == 204
    
    # Verify it's gone
    response = client.get(f'/books/{book_id}')
    assert response.status_code == 404

def test_delete_book_not_found(client):
    response = client.delete('/books/99999')
    assert response.status_code == 404
