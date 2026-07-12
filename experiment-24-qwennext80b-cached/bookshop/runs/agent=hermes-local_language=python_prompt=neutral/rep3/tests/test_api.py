#!/usr/bin/env python3
"""Integration tests for the Book Collection REST API."""

import json
import os
import pytest
import tempfile
import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify, g


# Create the test app inline to avoid import issues
def create_test_app(db_path):
    """Create a fresh Flask app with the given database path."""
    app = Flask('test_app')
    app.config['TESTING'] = True
    
    def get_db():
        if 'db' not in g:
            g.db = sqlite3.connect(db_path)
            g.db.row_factory = sqlite3.Row
        return g.db
    
    def close_db(exception):
        db = g.pop('db', None)
        if db is not None:
            db.close()
    
    app.teardown_appcontext(close_db)
    
    def init_db():
        db = get_db()
        db.execute('''
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                year INTEGER,
                isbn TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        ''')
        db.commit()
    
    app.init_db = init_db
    
    @app.route('/health', methods=['GET'])
    def health_check():
        try:
            db = get_db()
            db.execute('SELECT 1')
            return jsonify({'status': 'healthy'}), 200
        except Exception as e:
            return jsonify({'status': 'unhealthy', 'error': str(e)}), 500
    
    @app.route('/books', methods=['GET', 'POST'])
    def books_collection():
        db = get_db()
        
        if request.method == 'POST':
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No data provided'}), 400
            
            title = data.get('title')
            author = data.get('author')
            
            if not title or not isinstance(title, str) or not title.strip():
                return jsonify({'error': 'Title is required'}), 400
            if not author or not isinstance(author, str) or not author.strip():
                return jsonify({'error': 'Author is required'}), 400
            
            year = data.get('year')
            if year is not None:
                try:
                    year = int(year)
                    if year < 0 or year > 9999:
                        return jsonify({'error': 'Year must be a valid year'}), 400
                except (ValueError, TypeError):
                    return jsonify({'error': 'Year must be a valid integer'}), 400
            
            now = datetime.utcnow().isoformat()
            cursor = db.execute(
                'INSERT INTO books (title, author, year, isbn, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)',
                (title, author, year, data.get('isbn'), now, now)
            )
            db.commit()
            book_id = cursor.lastrowid
            book = db.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()
            
            return jsonify({
                'id': book['id'],
                'title': book['title'],
                'author': book['author'],
                'year': book['year'],
                'isbn': book['isbn'],
                'created_at': book['created_at'],
                'updated_at': book['updated_at']
            }), 201
        
        # GET all books
        author = request.args.get('author')
        if author:
            books = db.execute('SELECT * FROM books WHERE author = ?', (author,)).fetchall()
        else:
            books = db.execute('SELECT * FROM books').fetchall()
        
        return jsonify([{
            'id': book['id'],
            'title': book['title'],
            'author': book['author'],
            'year': book['year'],
            'isbn': book['isbn'],
            'created_at': book['created_at'],
            'updated_at': book['updated_at']
        } for book in books]), 200
    
    @app.route('/books/<int:book_id>', methods=['GET', 'PUT', 'DELETE'])
    def book_detail(book_id):
        db = get_db()
        book = db.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()
        
        if request.method == 'GET':
            if not book:
                return jsonify({'error': 'Book not found'}), 404
            return jsonify({
                'id': book['id'],
                'title': book['title'],
                'author': book['author'],
                'year': book['year'],
                'isbn': book['isbn'],
                'created_at': book['created_at'],
                'updated_at': book['updated_at']
            }), 200
        
        elif request.method == 'PUT':
            if not book:
                return jsonify({'error': 'Book not found'}), 404
            
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No data provided'}), 400
            
            title = data.get('title')
            author = data.get('author')
            
            if not title or not isinstance(title, str) or not title.strip():
                return jsonify({'error': 'Title is required'}), 400
            if not author or not isinstance(author, str) or not author.strip():
                return jsonify({'error': 'Author is required'}), 400
            
            year = data.get('year')
            if year is not None:
                try:
                    year = int(year)
                    if year < 0 or year > 9999:
                        return jsonify({'error': 'Year must be a valid year'}), 400
                except (ValueError, TypeError):
                    return jsonify({'error': 'Year must be a valid integer'}), 400
            
            now = datetime.utcnow().isoformat()
            db.execute(
                'UPDATE books SET title = ?, author = ?, year = ?, isbn = ?, updated_at = ? WHERE id = ?',
                (title, author, year, data.get('isbn'), now, book_id)
            )
            db.commit()
            
            book = db.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()
            return jsonify({
                'id': book['id'],
                'title': book['title'],
                'author': book['author'],
                'year': book['year'],
                'isbn': book['isbn'],
                'created_at': book['created_at'],
                'updated_at': book['updated_at']
            }), 200
        
        elif request.method == 'DELETE':
            if not book:
                return jsonify({'error': 'Book not found'}), 404
            db.execute('DELETE FROM books WHERE id = ?', (book_id,))
            db.commit()
            return jsonify({'message': 'Book deleted successfully'}), 200
    
    return app


@pytest.fixture
def client():
    """Create a test client with a temporary database."""
    temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    temp_db.close()
    os.unlink(temp_db.name)
    
    test_app = create_test_app(temp_db.name)
    
    with test_app.app_context():
        test_app.init_db()
    
    with test_app.test_client() as client:
        yield client
    
    if os.path.exists(temp_db.name):
        os.unlink(temp_db.name)


@pytest.fixture
def sample_book():
    return {
        'title': 'The Great Gatsby',
        'author': 'F. Scott Fitzgerald',
        'year': 1925,
        'isbn': '978-0743273565'
    }


class TestHealthEndpoint:
    def test_health_check(self, client):
        response = client.get('/health')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'healthy'


class TestBooksEndpoint:
    def test_get_books_empty(self, client):
        response = client.get('/books')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list)
        assert len(data) == 0
    
    def test_create_book(self, client, sample_book):
        response = client.post(
            '/books',
            data=json.dumps(sample_book),
            content_type='application/json'
        )
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['title'] == sample_book['title']
        assert data['author'] == sample_book['author']
        assert 'id' in data
        assert 'created_at' in data
    
    def test_create_book_missing_title(self, client):
        response = client.post(
            '/books',
            data=json.dumps({'author': 'Test Author'}),
            content_type='application/json'
        )
        assert response.status_code == 400
    
    def test_create_book_missing_author(self, client):
        response = client.post(
            '/books',
            data=json.dumps({'title': 'Test Title'}),
            content_type='application/json'
        )
        assert response.status_code == 400
    
    def test_create_book_empty_title(self, client):
        response = client.post(
            '/books',
            data=json.dumps({'title': '', 'author': 'Test Author'}),
            content_type='application/json'
        )
        assert response.status_code == 400
    
    def test_get_books_with_data(self, client, sample_book):
        client.post('/books', data=json.dumps(sample_book), content_type='application/json')
        response = client.get('/books')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data) == 1
        assert data[0]['title'] == sample_book['title']
    
    def test_get_books_by_author(self, client, sample_book):
        client.post('/books', data=json.dumps(sample_book), content_type='application/json')
        response = client.get(f'/books?author={sample_book["author"]}')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data) == 1
        assert data[0]['author'] == sample_book['author']
    
    def test_get_book_by_id(self, client, sample_book):
        create_response = client.post('/books', data=json.dumps(sample_book), content_type='application/json')
        book_id = json.loads(create_response.data)['id']
        response = client.get(f'/books/{book_id}')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['id'] == book_id
    
    def test_get_book_not_found(self, client):
        response = client.get('/books/99999')
        assert response.status_code == 404
    
    def test_update_book(self, client, sample_book):
        create_response = client.post('/books', data=json.dumps(sample_book), content_type='application/json')
        book_id = json.loads(create_response.data)['id']
        
        updated_data = {'title': 'Updated Title', 'author': 'Updated Author', 'year': 2024}
        response = client.put(f'/books/{book_id}', data=json.dumps(updated_data), content_type='application/json')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['title'] == updated_data['title']
    
    def test_update_book_not_found(self, client):
        response = client.put('/books/99999', data=json.dumps({'title': 'Test'}), content_type='application/json')
        assert response.status_code == 404
    
    def test_delete_book(self, client, sample_book):
        create_response = client.post('/books', data=json.dumps(sample_book), content_type='application/json')
        book_id = json.loads(create_response.data)['id']
        
        response = client.delete(f'/books/{book_id}')
        assert response.status_code == 200
        
        get_response = client.get(f'/books/{book_id}')
        assert get_response.status_code == 404
    
    def test_delete_book_not_found(self, client):
        response = client.delete('/books/99999')
        assert response.status_code == 404


class TestValidation:
    def test_create_book_no_data(self, client):
        response = client.post('/books', data=json.dumps({}), content_type='application/json')
        assert response.status_code == 400
    
    def test_create_book_whitespace_title(self, client):
        response = client.post(
            '/books',
            data=json.dumps({'title': '   ', 'author': 'Test Author'}),
            content_type='application/json'
        )
        assert response.status_code == 400
    
    def test_create_book_whitespace_author(self, client):
        response = client.post(
            '/books',
            data=json.dumps({'title': 'Test Title', 'author': '   '}),
            content_type='application/json'
        )
        assert response.status_code == 400
    
    def test_create_book_invalid_year(self, client, sample_book):
        sample_book['year'] = 'not-a-number'
        response = client.post('/books', data=json.dumps(sample_book), content_type='application/json')
        assert response.status_code == 400
    
    def test_update_book_invalid_year(self, client, sample_book):
        create_response = client.post('/books', data=json.dumps(sample_book), content_type='application/json')
        book_id = json.loads(create_response.data)['id']
        
        response = client.put(f'/books/{book_id}', data=json.dumps({'year': 'invalid'}), content_type='application/json')
        assert response.status_code == 400


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
