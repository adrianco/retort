#!/usr/bin/env python3
"""Book API REST Service - Flask application for managing a book collection."""

import sqlite3
import json
import os
from datetime import datetime, timezone
from flask import Flask, request, jsonify, g

app = Flask(__name__)

# Default database file
DEFAULT_DATABASE = os.environ.get('BOOK_API_DATABASE', 'books.db')
# For testing, use a fresh in-memory database
_testing_db = None


def get_db():
    """Get database connection for current request context."""
    if _testing_db is not None:
        return _testing_db
    if 'db' not in g:
        g.db = sqlite3.connect(DEFAULT_DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception):
    """Close database connection at end of request."""
    if _testing_db is not None:
        return
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    """Initialize the database with required tables."""
    db = get_db()
    cursor = db.cursor()
    cursor.execute('''
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


def reset_db():
    """Reset the database for testing - drops and recreates tables."""
    global _testing_db
    db = get_db()
    cursor = db.cursor()
    cursor.execute('DROP TABLE IF EXISTS books')
    cursor.execute('''
        CREATE TABLE books (
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


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    }), 200


@app.route('/books', methods=['GET'])
def list_books():
    """List all books, optionally filtered by author."""
    db = get_db()
    cursor = db.cursor()
    
    author = request.args.get('author')
    
    if author:
        cursor.execute(
            'SELECT * FROM books WHERE author = ? ORDER BY id',
            (author,)
        )
    else:
        cursor.execute('SELECT * FROM books ORDER BY id')
    
    books = []
    for row in cursor.fetchall():
        books.append({
            'id': row['id'],
            'title': row['title'],
            'author': row['author'],
            'year': row['year'],
            'isbn': row['isbn'],
            'created_at': row['created_at'],
            'updated_at': row['updated_at']
        })
    
    return jsonify(books), 200


@app.route('/books', methods=['POST'])
def create_book():
    """Create a new book."""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'Request body is required'}), 400
    
    # Validation
    errors = []
    if not data.get('title'):
        errors.append('title is required')
    if not data.get('author'):
        errors.append('author is required')
    
    if errors:
        return jsonify({'error': errors}), 400
    
    created_at = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    updated_at = created_at
    
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        '''INSERT INTO books (title, author, year, isbn, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?)''',
        (data['title'], data['author'], data.get('year'), data.get('isbn'), created_at, updated_at)
    )
    db.commit()
    
    book_id = cursor.lastrowid
    
    return jsonify({
        'id': book_id,
        'title': data['title'],
        'author': data['author'],
        'year': data.get('year'),
        'isbn': data.get('isbn'),
        'created_at': created_at,
        'updated_at': updated_at
    }), 201


@app.route('/books/<int:book_id>', methods=['GET'])
def get_book(book_id):
    """Get a single book by ID."""
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM books WHERE id = ?', (book_id,))
    row = cursor.fetchone()
    
    if not row:
        return jsonify({'error': 'Book not found'}), 404
    
    book = {
        'id': row['id'],
        'title': row['title'],
        'author': row['author'],
        'year': row['year'],
        'isbn': row['isbn'],
        'created_at': row['created_at'],
        'updated_at': row['updated_at']
    }
    
    return jsonify(book), 200


@app.route('/books/<int:book_id>', methods=['PUT'])
def update_book(book_id):
    """Update a book."""
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM books WHERE id = ?', (book_id,))
    row = cursor.fetchone()
    
    if not row:
        return jsonify({'error': 'Book not found'}), 404
    
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'Request body is required'}), 400
    
    # Validation
    errors = []
    if 'title' in data and not data['title']:
        errors.append('title cannot be empty')
    if 'author' in data and not data['author']:
        errors.append('author cannot be empty')
    
    if errors:
        return jsonify({'error': errors}), 400
    
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
        updates.append('year = ?')
        values.append(data['year'])
    if 'isbn' in data:
        updates.append('isbn = ?')
        values.append(data['isbn'])
    
    updated_at = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    updates.append('updated_at = ?')
    values.append(updated_at)
    
    values.append(book_id)
    
    cursor.execute(
        f'UPDATE books SET {", ".join(updates)} WHERE id = ?',
        tuple(values)
    )
    db.commit()
    
    # Fetch updated book
    cursor.execute('SELECT * FROM books WHERE id = ?', (book_id,))
    row = cursor.fetchone()
    
    book = {
        'id': row['id'],
        'title': row['title'],
        'author': row['author'],
        'year': row['year'],
        'isbn': row['isbn'],
        'created_at': row['created_at'],
        'updated_at': row['updated_at']
    }
    
    return jsonify(book), 200


@app.route('/books/<int:book_id>', methods=['DELETE'])
def delete_book(book_id):
    """Delete a book."""
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM books WHERE id = ?', (book_id,))
    row = cursor.fetchone()
    
    if not row:
        return jsonify({'error': 'Book not found'}), 404
    
    cursor.execute('DELETE FROM books WHERE id = ?', (book_id,))
    db.commit()
    
    return jsonify({'message': 'Book deleted'}), 200


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'false').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug)
