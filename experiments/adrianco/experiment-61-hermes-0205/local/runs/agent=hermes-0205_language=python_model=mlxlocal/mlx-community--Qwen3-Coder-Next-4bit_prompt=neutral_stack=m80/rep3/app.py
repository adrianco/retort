#!/usr/bin/env python3
"""Book Collection REST API Service."""

import sqlite3
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
    db = get_db()
    db.execute('''
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER,
            isbn TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT
        )
    ''')
    db.commit()


@app.before_request
def before_request():
    """Initialize database before first request."""
    if not hasattr(app, 'db_initialized'):
        init_db()
        app.db_initialized = True


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({'status': 'healthy'}), 200


@app.route('/books', methods=['GET'])
def list_books():
    """List all books, optionally filtered by author."""
    db = get_db()
    author = request.args.get('author')
    
    if author:
        cursor = db.execute(
            'SELECT * FROM books WHERE author = ?', 
            (author,)
        )
    else:
        cursor = db.execute('SELECT * FROM books')
    
    books = [dict(row) for row in cursor.fetchall()]
    return jsonify({'books': books, 'count': len(books)}), 200


@app.route('/books', methods=['POST'])
def create_book():
    """Create a new book."""
    data = request.get_json()
    
    # Validation
    errors = []
    if not data:
        return jsonify({'error': 'Request body is required'}), 400
    if 'title' not in data or not data['title']:
        errors.append('title is required')
    if 'author' not in data or not data['author']:
        errors.append('author is required')
    
    if errors:
        return jsonify({'errors': errors}), 400
    
    # Validate title and author are strings
    if not isinstance(data['title'], str):
        return jsonify({'errors': ['title must be a string']}), 400
    if not isinstance(data['author'], str):
        return jsonify({'errors': ['author must be a string']}), 400
    
    # Validate year if provided
    year = data.get('year')
    if year is not None:
        try:
            year = int(year)
            if year < 0 or year > 9999:
                return jsonify({'errors': ['year must be a valid year (0-9999)']}), 400
        except (ValueError, TypeError):
            return jsonify({'errors': ['year must be a valid integer']}), 400
    
    # Validate isbn if provided
    isbn = data.get('isbn')
    if isbn is not None and not isinstance(isbn, str):
        return jsonify({'errors': ['isbn must be a string']}), 400
    
    created_at = datetime.utcnow().isoformat()
    updated_at = None
    
    db = get_db()
    cursor = db.execute(
        'INSERT INTO books (title, author, year, isbn, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)',
        (data['title'], data['author'], year, isbn, created_at, updated_at)
    )
    db.commit()
    
    book_id = cursor.lastrowid
    
    return jsonify({
        'id': book_id,
        'title': data['title'],
        'author': data['author'],
        'year': year,
        'isbn': isbn,
        'created_at': created_at
    }), 201


@app.route('/books/<int:book_id>', methods=['GET'])
def get_book(book_id):
    """Get a single book by ID."""
    db = get_db()
    cursor = db.execute('SELECT * FROM books WHERE id = ?', (book_id,))
    row = cursor.fetchone()
    
    if row is None:
        return jsonify({'error': 'Book not found'}), 404
    
    book = dict(row)
    return jsonify(book), 200


@app.route('/books/<int:book_id>', methods=['PUT'])
def update_book(book_id):
    """Update a book."""
    db = get_db()
    
    # Check if book exists
    cursor = db.execute('SELECT * FROM books WHERE id = ?', (book_id,))
    row = cursor.fetchone()
    
    if row is None:
        return jsonify({'error': 'Book not found'}), 404
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Request body is required'}), 400
    
    # Validation
    errors = []
    if 'title' in data:
        if not isinstance(data['title'], str) or not data['title']:
            errors.append('title must be a non-empty string')
    if 'author' in data:
        if not isinstance(data['author'], str) or not data['author']:
            errors.append('author must be a non-empty string')
    
    if errors:
        return jsonify({'errors': errors}), 400
    
    # Build update query dynamically
    updates = []
    values = []
    
    if 'title' in data:
        updates.append('title = ?')
        values.append(data['title'])
    if 'author' in data:
        updates.append('author = ?')
        values.append(data['author'])
    if 'year' in data:
        year = data['year']
        if year is not None:
            try:
                year = int(year)
                if year < 0 or year > 9999:
                    return jsonify({'errors': ['year must be a valid year (0-9999)']}), 400
            except (ValueError, TypeError):
                return jsonify({'errors': ['year must be a valid integer']}), 400
        updates.append('year = ?')
        values.append(year)
    if 'isbn' in data:
        isbn = data['isbn']
        if isbn is not None and not isinstance(isbn, str):
            return jsonify({'errors': ['isbn must be a string']}), 400
        updates.append('isbn = ?')
        values.append(isbn)
    
    # Add updated_at timestamp
    updated_at = datetime.utcnow().isoformat()
    updates.append('updated_at = ?')
    values.append(updated_at)
    
    values.append(book_id)
    
    query = f"UPDATE books SET {', '.join(updates)} WHERE id = ?"
    db.execute(query, values)
    db.commit()
    
    # Fetch updated book
    cursor = db.execute('SELECT * FROM books WHERE id = ?', (book_id,))
    book = dict(cursor.fetchone())
    
    return jsonify(book), 200


@app.route('/books/<int:book_id>', methods=['DELETE'])
def delete_book(book_id):
    """Delete a book."""
    db = get_db()
    
    # Check if book exists
    cursor = db.execute('SELECT * FROM books WHERE id = ?', (book_id,))
    row = cursor.fetchone()
    
    if row is None:
        return jsonify({'error': 'Book not found'}), 404
    
    db.execute('DELETE FROM books WHERE id = ?', (book_id,))
    db.commit()
    
    return jsonify({'message': 'Book deleted successfully'}), 200


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
