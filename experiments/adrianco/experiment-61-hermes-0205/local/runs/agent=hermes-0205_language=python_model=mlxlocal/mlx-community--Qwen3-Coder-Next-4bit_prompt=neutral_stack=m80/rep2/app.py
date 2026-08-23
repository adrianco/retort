#!/usr/bin/env python3
"""Book API REST Service - A REST API for managing a book collection."""

import sqlite3
import json
import re
from datetime import datetime
from flask import Flask, request, jsonify, g

app = Flask(__name__)
DATABASE = 'books.db'


def get_db():
    """Get database connection for current request context."""
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(error):
    """Close database connection at end of request."""
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    """Initialize the database with required tables."""
    db = sqlite3.connect(DATABASE)
    cursor = db.cursor()
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
    db.commit()
    db.close()


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()}), 200


@app.route('/books', methods=['POST'])
def create_book():
    """Create a new book."""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'Request body is required'}), 400
    
    # Validate required fields
    if 'title' not in data or not data['title']:
        return jsonify({'error': 'Title is required'}), 400
    if 'author' not in data or not data['author']:
        return jsonify({'error': 'Author is required'}), 400
    
    # Validate title and author are strings
    if not isinstance(data['title'], str):
        return jsonify({'error': 'Title must be a string'}), 400
    if not isinstance(data['author'], str):
        return jsonify({'error': 'Author must be a string'}), 400
    
    # Validate year if provided
    year = data.get('year')
    if year is not None:
        try:
            year = int(year)
            if year < 0 or year > 9999:
                return jsonify({'error': 'Year must be a valid year (0-9999)'}), 400
        except (ValueError, TypeError):
            return jsonify({'error': 'Year must be a valid integer'}), 400
    
    # Validate isbn if provided
    isbn = data.get('isbn')
    if isbn is not None and not isinstance(isbn, str):
        return jsonify({'error': 'ISBN must be a string'}), 400
    
    db = get_db()
    cursor = db.cursor()
    created_at = datetime.now().isoformat()
    updated_at = created_at
    
    cursor.execute(
        '''INSERT INTO books (title, author, year, isbn, created_at, updated_at) 
           VALUES (?, ?, ?, ?, ?, ?)''',
        (data['title'], data['author'], year, isbn, created_at, updated_at)
    )
    db.commit()
    
    book_id = cursor.lastrowid
    book = get_book_by_id(cursor, book_id)
    
    return jsonify(book), 201


@app.route('/books', methods=['GET'])
def list_books():
    """List all books, optionally filtered by author."""
    author = request.args.get('author')
    
    db = get_db()
    cursor = db.cursor()
    
    if author:
        cursor.execute('SELECT * FROM books WHERE author = ?', (author,))
    else:
        cursor.execute('SELECT * FROM books')
    
    books = cursor.fetchall()
    return jsonify([dict(book) for book in books]), 200


@app.route('/books/<int:book_id>', methods=['GET'])
def get_book(book_id):
    """Get a single book by ID."""
    db = get_db()
    cursor = db.cursor()
    book = get_book_by_id(cursor, book_id)
    
    if not book:
        return jsonify({'error': 'Book not found'}), 404
    
    return jsonify(book), 200


@app.route('/books/<int:book_id>', methods=['PUT'])
def update_book(book_id):
    """Update a book."""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'Request body is required'}), 400
    
    db = get_db()
    cursor = db.cursor()
    
    # Check if book exists
    book = get_book_by_id(cursor, book_id)
    if not book:
        return jsonify({'error': 'Book not found'}), 404
    
    # Validate title if provided
    if 'title' in data:
        if not data['title']:
            return jsonify({'error': 'Title cannot be empty'}), 400
        if not isinstance(data['title'], str):
            return jsonify({'error': 'Title must be a string'}), 400
    
    # Validate author if provided
    if 'author' in data:
        if not data['author']:
            return jsonify({'error': 'Author cannot be empty'}), 400
        if not isinstance(data['author'], str):
            return jsonify({'error': 'Author must be a string'}), 400
    
    # Validate year if provided
    year = data.get('year')
    if year is not None:
        try:
            year = int(year)
            if year < 0 or year > 9999:
                return jsonify({'error': 'Year must be a valid year (0-9999)'}), 400
        except (ValueError, TypeError):
            return jsonify({'error': 'Year must be a valid integer'}), 400
    
    # Validate isbn if provided
    isbn = data.get('isbn')
    if isbn is not None and not isinstance(isbn, str):
        return jsonify({'error': 'ISBN must be a string'}), 400
    
    # Build update query dynamically
    update_fields = []
    update_values = []
    
    if 'title' in data:
        update_fields.append('title = ?')
        update_values.append(data['title'])
    if 'author' in data:
        update_fields.append('author = ?')
        update_values.append(data['author'])
    if 'year' in data:
        update_fields.append('year = ?')
        update_values.append(year)
    if 'isbn' in data:
        update_fields.append('isbn = ?')
        update_values.append(isbn)
    
    updated_at = datetime.now().isoformat()
    update_fields.append('updated_at = ?')
    update_values.append(updated_at)
    update_values.append(book_id)
    
    query = f"UPDATE books SET {', '.join(update_fields)} WHERE id = ?"
    cursor.execute(query, update_values)
    db.commit()
    
    book = get_book_by_id(cursor, book_id)
    return jsonify(book), 200


@app.route('/books/<int:book_id>', methods=['DELETE'])
def delete_book(book_id):
    """Delete a book."""
    db = get_db()
    cursor = db.cursor()
    
    # Check if book exists
    book = get_book_by_id(cursor, book_id)
    if not book:
        return jsonify({'error': 'Book not found'}), 404
    
    cursor.execute('DELETE FROM books WHERE id = ?', (book_id,))
    db.commit()
    
    return jsonify({'message': 'Book deleted successfully'}), 200


def get_book_by_id(cursor, book_id):
    """Helper function to get a book by ID."""
    cursor.execute('SELECT * FROM books WHERE id = ?', (book_id,))
    row = cursor.fetchone()
    return dict(row) if row else None


# Initialize database on module import
init_db()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
