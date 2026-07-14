"""Book API REST Service - Manage a book collection with CRUD operations."""

import sqlite3
import os
from flask import Flask, request, jsonify, g

app = Flask(__name__)

DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'books.db')
_db_conn = None


def get_db():
    """Get a database connection for the current request."""
    global _db_conn

    if DATABASE == ':memory:':
        if _db_conn is None:
            _db_conn = sqlite3.connect(':memory:', check_same_thread=False)
            _db_conn.row_factory = sqlite3.Row
            # Create tables lazily on first use
            cursor = _db_conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS books (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    author TEXT NOT NULL,
                    year INTEGER,
                    isbn TEXT
                )
            ''')
            _db_conn.commit()
        return _db_conn

    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception):
    """Close the database connection at the end of each request."""
    if DATABASE == ':memory:':
        return
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    """Initialize the database and create tables.

    When DATABASE is ':memory:', recreates a shared in-memory connection
    with fresh tables. Call this from tests after setting DATABASE = ':memory:'
    to reset state between test functions.
    """
    global _db_conn

    if DATABASE == ':memory:':
        if _db_conn is not None:
            try:
                _db_conn.close()
            except Exception:
                pass
        # Don't create the connection here - let get_db() do it lazily
        _db_conn = None
    else:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('''
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


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({'status': 'healthy'}), 200


@app.route('/books', methods=['POST'])
def create_book():
    """Create a new book."""
    data = request.get_json()

    if not data:
        return jsonify({'error': 'Request body must be JSON'}), 400

    title = data.get('title')
    author = data.get('author')

    if not title or not str(title).strip():
        return jsonify({'error': 'Title is required'}), 400

    if not author or not str(author).strip():
        return jsonify({'error': 'Author is required'}), 400

    year = data.get('year')
    isbn = data.get('isbn')

    if year is not None:
        try:
            year = int(year)
        except (ValueError, TypeError):
            return jsonify({'error': 'Year must be an integer'}), 400

    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        'INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)',
        (str(title).strip(), str(author).strip(), year, isbn)
    )
    db.commit()

    book_id = cursor.lastrowid

    return jsonify({
        'id': book_id,
        'title': str(title).strip(),
        'author': str(author).strip(),
        'year': year,
        'isbn': isbn
    }), 201


@app.route('/books', methods=['GET'])
def list_books():
    """List all books, with optional author filter."""
    db = get_db()
    cursor = db.cursor()

    author_filter = request.args.get('author')

    if author_filter:
        cursor.execute(
            'SELECT * FROM books WHERE author LIKE ?',
            ('%' + author_filter + '%',)
        )
    else:
        cursor.execute('SELECT * FROM books')

    rows = cursor.fetchall()
    books = [dict(row) for row in rows]

    return jsonify(books), 200


@app.route('/books/<int:book_id>', methods=['GET'])
def get_book(book_id):
    """Get a single book by ID."""
    db = get_db()
    cursor = db.cursor()

    cursor.execute('SELECT * FROM books WHERE id = ?', (book_id,))
    row = cursor.fetchone()

    if row is None:
        return jsonify({'error': 'Book not found'}), 404

    return jsonify(dict(row)), 200


@app.route('/books/<int:book_id>', methods=['PUT'])
def update_book(book_id):
    """Update a book."""
    db = get_db()
    cursor = db.cursor()

    # Check if book exists
    cursor.execute('SELECT * FROM books WHERE id = ?', (book_id,))
    existing = cursor.fetchone()

    if existing is None:
        return jsonify({'error': 'Book not found'}), 404

    data = request.get_json()
    if not data:
        return jsonify({'error': 'Request body must be JSON'}), 400

    title = data.get('title', existing['title'])
    author = data.get('author', existing['author'])

    if not str(title).strip():
        return jsonify({'error': 'Title is required'}), 400

    if not str(author).strip():
        return jsonify({'error': 'Author is required'}), 400

    year = data.get('year', existing['year'])
    isbn = data.get('isbn', existing['isbn'])

    if year is not None:
        try:
            year = int(year)
        except (ValueError, TypeError):
            return jsonify({'error': 'Year must be an integer'}), 400

    cursor.execute(
        '''UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?''',
        (str(title).strip(), str(author).strip(), year, isbn, book_id)
    )
    db.commit()

    return jsonify({
        'id': book_id,
        'title': str(title).strip(),
        'author': str(author).strip(),
        'year': year,
        'isbn': isbn
    }), 200


@app.route('/books/<int:book_id>', methods=['DELETE'])
def delete_book(book_id):
    """Delete a book."""
    db = get_db()
    cursor = db.cursor()

    # Check if book exists
    cursor.execute('SELECT * FROM books WHERE id = ?', (book_id,))
    existing = cursor.fetchone()

    if existing is None:
        return jsonify({'error': 'Book not found'}), 404

    cursor.execute('DELETE FROM books WHERE id = ?', (book_id,))
    db.commit()

    return jsonify({'message': 'Book deleted successfully'}), 200


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
