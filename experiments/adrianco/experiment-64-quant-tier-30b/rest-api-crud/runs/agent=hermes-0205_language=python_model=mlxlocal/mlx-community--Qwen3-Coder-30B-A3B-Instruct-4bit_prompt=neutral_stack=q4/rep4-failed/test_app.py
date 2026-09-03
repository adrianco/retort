import pytest
import sys
import os

# Add the project root directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, init_db
import sqlite3
import json

@pytest.fixture
def client():
    """Create a test client"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        with app.app_context():
            init_db()
        yield client

def test_health_check(client):
    """Test health check endpoint"""
    response = client.get('/health')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'status' in data
    assert data['status'] == 'healthy'

def test_create_book_success(client):
    """Test creating a book successfully"""
    response = client.post('/books', 
                           data=json.dumps({
                               'title': 'Test Book',
 'author': 'Test Author',
 'year': 2020,
 'isbn': '1234567890'
                           }),
                           content_type='application/json')
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data['title'] == 'Test Book'
    assert data['author'] == 'Test Author'
    assert data['year'] == 2020
    assert data['isbn'] == '1234567890'

def test_create_book_missing_title(client):
    """Test creating a book with missing title"""
    response = client.post('/books', 
                           data=json.dumps({
                               'author': 'Test Author',
 'isbn': '1234567890'
                           }),
                           content_type='application/json')
    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'error' in data

def test_create_book_missing_author(client):
    """Test creating a book with missing author"""
    response = client.post('/books', 
                           data=json.dumps({
                               'title': 'Test Book'
                           }),
                           content_type='application/json')
    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'error' in data

def test_get_book_success(client):
    """Test getting a single book by ID"""
    response = client.post('/books', 
                           data=json.dumps({
                               'title': 'Test Book',
 'author': 'Test Author',
 'year': 2020,
 'isbn': '1234567890'
                           }),
                           content_type='application/json')
    data = json.loads(response.data)
    book_id = data['id']
    
    response = client.get(f'/books/{book_id}')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['title'] == 'Test Book'
    assert data['author'] == 'Test Author'
    assert data['year'] == 2020
    assert data['isbn'] == '1234567890'

def test_update_book_success(client):
    """Test updating a book successfully"""
    response = client.post('/books', 
                           data=json.dumps({
                               'title': 'Original Title',
 'author': 'Original Author',
 'year': 2020,
 'isbn': '1234567890'
                           }),
                           content_type='application/json')
    
    book_id = json.loads(response.data)['id']
    
    response = client.put(f'/books/{book_id}', 
                          data=json.dumps({
                              'title': 'Updated Title',
 'author': 'Updated Author',
 'year': 2021,
 'isbn': '0987654321'
                          }),
                          content_type='application/json')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['title'] == 'Updated Title'
    assert data['author'] == 'Updated Author'
    assert data['year'] == 2021
    assert data['isbn'] == '0987654321'

def test_delete_book_success(client):
    """Test deleting a book successfully"""
    response = client.post('/books', 
                           data=json.dumps({
                               'title': 'Test Book',
 'author': 'Test Author',
 'year': 2020,
 'isbn': '1234567890'
                           }),
                           content_type='application/json')
    
    book_id = json.loads(response.data)['id']
    
    response = client.delete(f'/books/{book_id}')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'message' in data

def test_get_nonexistent_book(client):
    """Test getting a non-existent book"""
    response = client.get('/books/999999')
    assert response.status_code == 404

def test_list_books_with_filter(client):
    """Test listing books with author filter"""
    response = client.post('/books', 
                           data=json.dumps({
                               'title': 'Book 1',
 'author': 'Author A',
 'year': 2020,
 'isbn': '1234567890'
                           }),
                           content_type='application/json')
    
    response = client.post('/books', 
                           data=json.dumps({
               'title': 'Book 2',
 'author': 'Author B',
 'year': 2021,
 'isbn': '0987654321'
                           }),
                           content_type='application/json')
    
    response = client.get('/books?author=Author A')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) == 1
    assert data[0]['author'] == 'Author A'

def test_create_book_duplicate_isbn(client):
    """Test creating a book with duplicate ISBN"""
    response = client.post('/books', 
                           data=json.dumps({
                               'title': 'Book 1',
 'author': 'Author A',
 'isbn': '1234567890'
           }),
           content_type='application/json')
    
    response = client.post('/books', 
                           data=json.dumps({
                               'title': 'Book 2',
 'author': 'Author B',
 'isbn': '1234567890'
           }),
           content_type='application/json')
    
    assert response.status_code == 400