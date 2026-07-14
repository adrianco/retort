"""
Book API REST Service - A complete REST API for managing a book collection.

Endpoints:
    POST   /books         - Create a new book
    GET    /books         - List all books (support ?author= filter)
    GET    /books/<id>    - Get a single book by ID
    PUT    /books/<id>    - Update a book
    DELETE /books/<id>    - Delete a book
    GET    /health        - Health check

Storage: SQLite database (books.db)
"""
import sqlite3
import os
import json
from flask import Flask, request, jsonify, g

app = Flask(__name__)
DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'books.db')


def get_db():
    """Get a database connection for the current request."""
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA journal_mode=WAL")
    return g.db


@app.teardown_appcontext
def close_db(exception):
    """Close the database connection at the end of the request."""
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    """Initialize the database schema."""
    conn = sqlite3.connect(DATABASE)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER,
            isbn TEXT
        )
    ''')
    conn.commit()
    conn.close()


def book_to_dict(row):
    """Convert a database row to a dictionary."""
    return {
        'id': row['id'],
        'title': row['title'],
        'author': row['author'],
        'year': row['year'],
        'isbn': row['isbn']
    }


def validate_book_data(data, check_empty=True):
    """
    Validate book data from a JSON payload.
    
    Returns (is_valid, error_message) tuple.
    - title is required and must be non-empty if check_empty is True
    - author is required and must be non-empty if check_empty is True
    """
    if not data:
        return False, "Request body must be JSON"
    
    if check_empty:
        if 'title' not in data or not data.get('title', '').strip():
            return False, "Title is required"
        if 'author' not in data or not data.get('author', '').strip():
            return False, "Author is required"
    else:
        if 'title' in data and not data.get('title', '').strip():
            return False, "Title is required"
        if 'author' in data and not data.get('author', '').strip():
            return False, "Author is required"
    
    return True, None


# --- Health Check ---
@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({'status': 'ok'}), 200


# --- Create Book --- POST /books
@app.route('/books', methods=['POST'])
def create_book():
    """Create a new book."""
    data = request.get_json(force=True, silent=True)
    
    is_valid, error = validate_book_data(data, check_empty=True)
    if not is_valid:
        return jsonify({'error': error}), 400
    
    title = data['title'].strip()
    author = data['author'].strip()
    year = data.get('year')
    isbn = data.get('isbn')
    
    db = get_db()
    cursor = db.execute(
        'INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)',
        (title, author, year, isbn)
    )
    db.commit()
    
    book_id = cursor.lastrowid
    book = {
        'id': book_id,
        'title': title,
        'author': author,
        'year': year,
        'isbn': isbn
    }
    
    return jsonify(book), 201


# --- List Books --- GET /books
@app.route('/books', methods=['GET'])
def list_books():
    """List all books, with optional ?author= filter."""
    db = get_db()
    
    author_filter = request.args.get('author')
    
    if author_filter:
        rows = db.execute(
            'SELECT * FROM books WHERE author = ? ORDER BY id ASC',
            (author_filter,)
        ).fetchall()
    else:
        rows = db.execute('SELECT * FROM books ORDER BY id ASC').fetchall()
    
    books = [book_to_dict(row) for row in rows]
    return jsonify(books), 200


# --- Get Single Book --- GET /books/<id>
@app.route('/books/<int:book_id>', methods=['GET'])
def get_book(book_id):
    """Get a single book by ID."""
    db = get_db()
    row = db.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()
    
    if row is None:
        return jsonify({'error': 'Book not found'}), 404
    
    return jsonify(book_to_dict(row)), 200


# --- Update Book --- PUT /books/<id>
@app.route('/books/<int:book_id>', methods=['PUT'])
def update_book(book_id):
    """Update a book."""
    db = get_db()
    row = db.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()
    
    if row is None:
        return jsonify({'error': 'Book not found'}), 404
    
    data = request.get_json(force=True, silent=True)
    
    is_valid, error = validate_book_data(data, check_empty=False)
    if not is_valid:
        return jsonify({'error': error}), 400
    
    title = data.get('title', row['title']).strip()
    author = data.get('author', row['author']).strip()
    year = data.get('year', row['year'])
    isbn = data.get('isbn', row['isbn'])
    
    db.execute(
        'UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?',
        (title, author, year, isbn, book_id)
    )
    db.commit()
    
    updated = db.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()
    return jsonify(book_to_dict(updated)), 200


# --- Delete Book --- DELETE /books/<id>
@app.route('/books/<int:book_id>', methods=['DELETE'])
def delete_book(book_id):
    """Delete a book."""
    db = get_db()
    row = db.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()
    
    if row is None:
        return jsonify({'error': 'Book not found'}), 404
    
    db.execute('DELETE FROM books WHERE id = ?', (book_id,))
    db.commit()
    
    return jsonify({'message': 'Book deleted successfully'}), 200


# --- Initialize and Run ---
init_db()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
