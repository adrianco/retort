"""Book API REST Service - Flask application for managing a book collection."""

import sqlite3
import json
from datetime import datetime
from flask import Flask, request, jsonify, g

app = Flask(__name__)
DATABASE = 'books.db'


def get_db():
    """Get database connection for current request context."""
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db


@app.teardown_appcontext
def close_connection(exception):
    """Close database connection at end of request."""
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


def init_db():
    """Initialize the database with the books table."""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''
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
    conn.commit()
    conn.close()


def validate_book_data(data, require_title=True, require_author=True):
    """Validate book data from request body."""
    errors = []
    
    if require_title:
        if 'title' not in data or not data['title'] or not str(data['title']).strip():
            errors.append('title is required')
    
    if require_author:
        if 'author' not in data or not data['author'] or not str(data['author']).strip():
            errors.append('author is required')
    
    if 'year' in data and data['year'] is not None:
        try:
            year = int(data['year'])
            if year < 0 or year > 9999:
                errors.append('year must be a valid year (0-9999)')
        except (ValueError, TypeError):
            errors.append('year must be a valid integer')
    
    if 'isbn' in data and data['isbn'] is not None:
        if not str(data['isbn']).strip():
            errors.append('isbn cannot be empty')
    
    return errors


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute('SELECT 1')
        cursor.fetchone()
        return jsonify({'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()}), 200
    except Exception as e:
        return jsonify({'status': 'unhealthy', 'error': str(e), 'timestamp': datetime.utcnow().isoformat()}), 500


@app.route('/books', methods=['GET'])
def get_books():
    """Get all books, optionally filtered by author."""
    db = get_db()
    cursor = db.cursor()
    
    author = request.args.get('author')
    
    if author:
        cursor.execute('SELECT * FROM books WHERE author = ?', (author,))
    else:
        cursor.execute('SELECT * FROM books')
    
    books = cursor.fetchall()
    result = []
    for book in books:
        result.append({
            'id': book['id'],
            'title': book['title'],
            'author': book['author'],
            'year': book['year'],
            'isbn': book['isbn'],
            'created_at': book['created_at'],
            'updated_at': book['updated_at']
        })
    
    return jsonify(result), 200


@app.route('/books', methods=['POST'])
def create_book():
    """Create a new book."""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'Request body must be JSON'}), 400
    
    errors = validate_book_data(data)
    if errors:
        return jsonify({'error': errors}), 400
    
    now = datetime.utcnow().isoformat()
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute('''
        INSERT INTO books (title, author, year, isbn, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        str(data['title']).strip(),
        str(data['author']).strip(),
        data.get('year'),
        data.get('isbn'),
        now,
        now
    ))
    db.commit()
    
    book_id = cursor.lastrowid
    
    cursor.execute('SELECT * FROM books WHERE id = ?', (book_id,))
    book = cursor.fetchone()
    
    result = {
        'id': book['id'],
        'title': book['title'],
        'author': book['author'],
        'year': book['year'],
        'isbn': book['isbn'],
        'created_at': book['created_at'],
        'updated_at': book['updated_at']
    }
    
    return jsonify(result), 201


@app.route('/books/<int:book_id>', methods=['GET'])
def get_book(book_id):
    """Get a single book by ID."""
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute('SELECT * FROM books WHERE id = ?', (book_id,))
    book = cursor.fetchone()
    
    if not book:
        return jsonify({'error': 'Book not found'}), 404
    
    result = {
        'id': book['id'],
        'title': book['title'],
        'author': book['author'],
        'year': book['year'],
        'isbn': book['isbn'],
        'created_at': book['created_at'],
        'updated_at': book['updated_at']
    }
    
    return jsonify(result), 200


@app.route('/books/<int:book_id>', methods=['PUT'])
def update_book(book_id):
    """Update a book."""
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute('SELECT * FROM books WHERE id = ?', (book_id,))
    existing_book = cursor.fetchone()
    
    if not existing_book:
        return jsonify({'error': 'Book not found'}), 404
    
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'Request body must be JSON'}), 400
    
    errors = validate_book_data(data, require_title=False, require_author=False)
    if errors:
        return jsonify({'error': errors}), 400
    
    # Validate that title and author are not empty/whitespace when provided
    if 'title' in data and data['title'] is not None and not str(data['title']).strip():
        errors.append('title cannot be empty')
    if 'author' in data and data['author'] is not None and not str(data['author']).strip():
        errors.append('author cannot be empty')
    
    if errors:
        return jsonify({'error': errors}), 400
    
    now = datetime.utcnow().isoformat()
    
    # Use existing values if not provided
    title = str(data.get('title', existing_book['title'])).strip() if data.get('title') is not None else existing_book['title']
    author = str(data.get('author', existing_book['author'])).strip() if data.get('author') is not None else existing_book['author']
    year = data.get('year', existing_book['year'])
    isbn = data.get('isbn', existing_book['isbn'])
    
    cursor.execute('''
        UPDATE books SET title = ?, author = ?, year = ?, isbn = ?, updated_at = ?
        WHERE id = ?
    ''', (title, author, year, isbn, now, book_id))
    db.commit()
    
    cursor.execute('SELECT * FROM books WHERE id = ?', (book_id,))
    book = cursor.fetchone()
    
    result = {
        'id': book['id'],
        'title': book['title'],
        'author': book['author'],
        'year': book['year'],
        'isbn': book['isbn'],
        'created_at': book['created_at'],
        'updated_at': book['updated_at']
    }
    
    return jsonify(result), 200


@app.route('/books/<int:book_id>', methods=['DELETE'])
def delete_book(book_id):
    """Delete a book."""
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute('SELECT * FROM books WHERE id = ?', (book_id,))
    existing_book = cursor.fetchone()
    
    if not existing_book:
        return jsonify({'error': 'Book not found'}), 404
    
    cursor.execute('DELETE FROM books WHERE id = ?', (book_id,))
    db.commit()
    
    return jsonify({'message': 'Book deleted successfully'}), 200


# Initialize database when app starts
init_db()


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
