#!/usr/bin/env python3
"""Book API REST Service - Flask application for managing a book collection."""

import sqlite3
import json
import os
from datetime import datetime
from flask import Flask, request, jsonify, g

app = Flask(__name__)
DATABASE = os.environ.get('BOOKS_DATABASE', 'books.db')


def get_db():
    """Get database connection for the current request context."""
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception):
    """Close database connection at the end of request."""
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    """Initialize the database with the books table."""
    db = sqlite3.connect(DATABASE)
    cursor = db.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER,
            isbn TEXT,
            created_at TEXT NOT NULL
        )
    ''')
    db.commit()
    db.close()


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat()
    }), 200


@app.route('/books', methods=['POST'])
def create_book():
    """Create a new book."""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'Request body is required'}), 400
    
    # Validate required fields
    if 'title' not in data or not data['title'].strip():
        return jsonify({'error': 'Title is required'}), 400
    
    if 'author' not in data or not data['author'].strip():
        return jsonify({'error': 'Author is required'}), 400
    
    db = get_db()
    cursor = db.cursor()
    created_at = datetime.utcnow().isoformat()
    
    cursor.execute(
        'INSERT INTO books (title, author, year, isbn, created_at) VALUES (?, ?, ?, ?, ?)',
        (data['title'], data['author'], data.get('year'), data.get('isbn'), created_at)
    )
    db.commit()
    
    book_id = cursor.lastrowid
    
    return jsonify({
        'id': book_id,
        'title': data['title'],
        'author': data['author'],
        'year': data.get('year'),
        'isbn': data.get('isbn'),
        'created_at': created_at
    }), 201


@app.route('/books', methods=['GET'])
def list_books():
    """List all books, with optional author filter."""
    author = request.args.get('author')
    
    db = get_db()
    cursor = db.cursor()
    
    if author:
        cursor.execute('SELECT * FROM books WHERE author = ?', (author,))
    else:
        cursor.execute('SELECT * FROM books')
    
    books = cursor.fetchall()
    
    return jsonify({
        'books': [dict(book) for book in books]
    }), 200


@app.route('/books/<int:book_id>', methods=['GET'])
def get_book(book_id):
    """Get a single book by ID."""
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute('SELECT * FROM books WHERE id = ?', (book_id,))
    book = cursor.fetchone()
    
    if book is None:
        return jsonify({'error': 'Book not found'}), 404
    
    return jsonify(dict(book)), 200


@app.route('/books/<int:book_id>', methods=['PUT'])
def update_book(book_id):
    """Update a book."""
    db = get_db()
    cursor = db.cursor()
    
    # Check if book exists
    cursor.execute('SELECT * FROM books WHERE id = ?', (book_id,))
    book = cursor.fetchone()
    
    if book is None:
        return jsonify({'error': 'Book not found'}), 404
    
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'Request body is required'}), 400
    
    # Validate required fields if provided
    if 'title' in data and not data['title'].strip():
        return jsonify({'error': 'Title cannot be empty'}), 400
    
    if 'author' in data and not data['author'].strip():
        return jsonify({'error': 'Author cannot be empty'}), 400
    
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
    
    if not updates:
        return jsonify({'error': 'At least one field to update is required'}), 400
    
    values.append(book_id)
    query = f'UPDATE books SET {", ".join(updates)} WHERE id = ?'
    cursor.execute(query, values)
    db.commit()
    
    # Fetch updated book
    cursor.execute('SELECT * FROM books WHERE id = ?', (book_id,))
    updated_book = cursor.fetchone()
    
    return jsonify(dict(updated_book)), 200


@app.route('/books/<int:book_id>', methods=['DELETE'])
def delete_book(book_id):
    """Delete a book."""
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute('SELECT * FROM books WHERE id = ?', (book_id,))
    book = cursor.fetchone()
    
    if book is None:
        return jsonify({'error': 'Book not found'}), 404
    
    cursor.execute('DELETE FROM books WHERE id = ?', (book_id,))
    db.commit()
    
    return jsonify({'message': 'Book deleted successfully'}), 200


if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)
