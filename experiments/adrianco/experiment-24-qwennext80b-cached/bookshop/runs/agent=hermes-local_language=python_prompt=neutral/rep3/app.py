#!/usr/bin/env python3
"""Book Collection REST API Service."""

import sqlite3
from datetime import datetime
from typing import Optional
from flask import Flask, request, jsonify, g
import os

app = Flask(__name__)
DATABASE = os.environ.get('DATABASE', 'books.db')


def get_db():
    """Get database connection for current request context."""
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception):
    """Close database connection at end of request."""
    db = g.pop('db', None)
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
            created_at TEXT,
            updated_at TEXT
        )
    ''')
    db.commit()


def validate_book(data: dict) -> Optional[tuple]:
    """Validate book data. Returns error message if invalid, None if valid."""
    if not data:
        return "No data provided", 400
    
    title = data.get('title')
    author = data.get('author')
    
    if not title or not isinstance(title, str) or not title.strip():
        return "Title is required", 400
    
    if not author or not isinstance(author, str) or not author.strip():
        return "Author is required", 400
    
    # Validate year if provided
    year = data.get('year')
    if year is not None:
        try:
            year = int(year)
            if year < 0 or year > 9999:
                return "Year must be a valid year (0-9999)", 400
        except (ValueError, TypeError):
            return "Year must be a valid integer", 400
    
    return None


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    try:
        db = get_db()
        db.execute('SELECT 1')
        return jsonify({'status': 'healthy'}), 200
    except Exception as e:
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 500


@app.route('/books', methods=['GET'])
def get_books():
    """Get all books, optionally filtered by author."""
    db = get_db()
    author = request.args.get('author')
    
    if author:
        books = db.execute(
            'SELECT * FROM books WHERE author = ?',
            (author,)
        ).fetchall()
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


@app.route('/books', methods=['POST'])
def create_book():
    """Create a new book."""
    data = request.get_json()
    error = validate_book(data)
    if error:
        return jsonify({'error': error[0]}), error[1]
    
    now = datetime.utcnow().isoformat()
    db = get_db()
    cursor = db.execute(
        'INSERT INTO books (title, author, year, isbn, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)',
        (data['title'], data['author'], data.get('year'), data.get('isbn'), now, now)
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


@app.route('/books/<int:book_id>', methods=['GET'])
def get_book(book_id):
    """Get a single book by ID."""
    db = get_db()
    book = db.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()
    
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


@app.route('/books/<int:book_id>', methods=['PUT'])
def update_book(book_id):
    """Update a book."""
    # Check if book exists
    db = get_db()
    existing_book = db.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()
    
    if not existing_book:
        return jsonify({'error': 'Book not found'}), 404
    
    data = request.get_json()
    error = validate_book(data)
    if error:
        return jsonify({'error': error[0]}), error[1]
    
    now = datetime.utcnow().isoformat()
    db.execute(
        'UPDATE books SET title = ?, author = ?, year = ?, isbn = ?, updated_at = ? WHERE id = ?',
        (data['title'], data['author'], data.get('year'), data.get('isbn'), now, book_id)
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


@app.route('/books/<int:book_id>', methods=['DELETE'])
def delete_book(book_id):
    """Delete a book."""
    db = get_db()
    book = db.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()
    
    if not book:
        return jsonify({'error': 'Book not found'}), 404
    
    db.execute('DELETE FROM books WHERE id = ?', (book_id,))
    db.commit()
    
    return jsonify({'message': 'Book deleted successfully'}), 200


if __name__ == '__main__':
    with app.app_context():
        init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)
