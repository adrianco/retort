import pytest
import sqlite3
import json
from app import app, init_db, DATABASE

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        with app.app_context():
            init_db()
        yield client
        with app.app_context():
            conn = sqlite3.connect(DATABASE)
            conn.execute('DELETE FROM books')
            conn.commit()

def test_health_check(client):
    rv = client.get('/health')
    json_data = rv.get_json()
    assert rv.status_code == 200
    assert json_data == {"status": "healthy"}

def test_create_book(client):
    # Test creating a book
    rv = client.post('/books', json={
        'title': '1984',
        'author': 'George Orwell',
        'year': 1949,
        'isbn': '0451524934'
    })
    json_data = rv.get_json()
    assert rv.status_code == 201
    assert json_data['title'] == '1984'
    assert json_data['author'] == 'George Orwell'
    assert 'id' in json_data
    
    # Test validation - missing required field
    rv = client.post('/books', json={
        'title': 'Animal Farm',
        'year': 1945
        # missing author
    })
    assert rv.status_code == 400

def test_list_books(client):
    # Add a test book
    conn = sqlite3.connect(DATABASE)
    conn.execute("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)", 
                 ('1984', 'George Orwell', 1949, '0451524934'))
    conn.commit()
    
    # Test listing all books
    rv = client.get('/books')
    json_data = rv.get_json()
    assert rv.status_code == 200
    assert len(json_data) == 1
    assert json_data[0]['title'] == '1984'
    
    # Test filtering by author
    rv = client.get('/books', query_string={'author': 'George Orwell'})
    json_data = rv.get_json()
    assert rv.status_code == 200
    assert len(json_data) == 1
    assert json_data[0]['author'] == 'George Orwell'
    
    # Test filtering with no matches
    rv = client.get('/books', query_string={'author': 'Mark Twain'})
    json_data = rv.get_json()
    assert rv.status_code == 200
    assert len(json_data) == 0

def test_get_book(client):
    # Add a test book
    conn = sqlite3.connect(DATABASE)
    cursor = conn.execute("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)", 
                         ('1984', 'George Orwell', 1949, '0451524934'))
    book_id = cursor.lastrowid
    conn.commit()
    
    # Test getting the book
    rv = client.get(f'/books/{book_id}')
    json_data = rv.get_json()
    assert rv.status_code == 200
    assert json_data['title'] == '1984'
    assert json_data['id'] == book_id
    
    # Test getting non-existent book
    rv = client.get('/books/9999')
    assert rv.status_code == 404

def test_update_book(client):
    # Add a test book
    conn = sqlite3.connect(DATABASE)
    cursor = conn.execute("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)", 
                         ('1984', 'George Orwell', 1949, '0451524934'))
    book_id = cursor.lastrowid
    conn.commit()
    
    # Test updating the book
    rv = client.put(f'/books/{book_id}', json={
        'title': 'Animal Farm',
        'author': 'George Orwell',
        'year': 1945,
        'isbn': '0452284236'
    })
    assert rv.status_code == 204
    
    # Verify the update
    rv = client.get(f'/books/{book_id}')
    json_data = rv.get_json()
    assert json_data['title'] == 'Animal Farm'
    assert json_data['year'] == 1945
    
    # Test validation - missing required field
    rv = client.put(f'/books/{book_id}', json={
        'title': 'Some Book',
        # missing author
    })
    assert rv.status_code == 400

def test_delete_book(client):
    # Add a test book
    conn = sqlite3.connect(DATABASE)
    cursor = conn.execute("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)", 
                         ('1984', 'George Orwell', 1949, '0451524934'))
    book_id = cursor.lastrowid
    conn.commit()
    
    # Test deleting the book
    rv = client.delete(f'/books/{book_id}')
    assert rv.status_code == 204
    
    # Verify deletion
    rv = client.get(f'/books/{book_id}')
    assert rv.status_code == 404
    
    # Test deleting non-existent book
    rv = client.delete('/books/9999')
    assert rv.status_code == 404
