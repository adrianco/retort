import sqlite3
import os
from flask import Flask, request, jsonify, g

app = Flask(__name__)

DATABASE = os.environ.get('DATABASE', 'books.db')
_db_initialized = False


def _ensure_schema():
    """Create the books table if it does not exist."""
    global _db_initialized
    if not _db_initialized:
        db = sqlite3.connect(DATABASE)
        db.execute('''
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                year INTEGER,
                isbn TEXT
            )
        ''')
        db.commit()
        db.close()
        _db_initialized = True


def get_db():
    """Get database connection for current request."""
    if 'db' not in g:
        _ensure_schema()
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute('PRAGMA journal_mode=WAL')
    return g.db


@app.teardown_appcontext
def close_db(exception):
    """Close database connection at end of request."""
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    """Initialize the database schema (convenience for tests)."""
    global _db_initialized
    _db_initialized = False
    _ensure_schema()


def book_to_dict(row):
    """Convert a sqlite3.Row to a dictionary."""
    return {
        'id': row['id'],
        'title': row['title'],
        'author': row['author'],
        'year': row['year'],
        'isbn': row['isbn']
    }


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

    title = str(title).strip()
    author = str(author).strip()
    year = data.get('year')
    isbn = data.get('isbn')

    if year is not None:
        try:
            year = int(year)
        except (ValueError, TypeError):
            return jsonify({'error': 'Year must be an integer'}), 400

    db = get_db()
    cursor = db.execute(
        'INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)',
        (title, author, year, isbn)
    )
    db.commit()
    book_id = cursor.lastrowid

    book = db.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()
    return jsonify(book_to_dict(book)), 201


@app.route('/books', methods=['GET'])
def list_books():
    """List all books, with optional author filter."""
    author = request.args.get('author')
    db = get_db()

    if author:
        rows = db.execute(
            'SELECT * FROM books WHERE author LIKE ?',
            (f'%{author}%',)
        ).fetchall()
    else:
        rows = db.execute('SELECT * FROM books').fetchall()

    return jsonify([book_to_dict(row) for row in rows]), 200


@app.route('/books/<int:book_id>', methods=['GET'])
def get_book(book_id):
    """Get a single book by ID."""
    db = get_db()
    book = db.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()
    if book is None:
        return jsonify({'error': 'Book not found'}), 404
    return jsonify(book_to_dict(book)), 200


@app.route('/books/<int:book_id>', methods=['PUT'])
def update_book(book_id):
    """Update a book."""
    db = get_db()
    book = db.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()
    if book is None:
        return jsonify({'error': 'Book not found'}), 404

    data = request.get_json()
    if not data:
        return jsonify({'error': 'Request body must be JSON'}), 400

    title = data.get('title', book['title'])
    author = data.get('author', book['author'])

    if not title or not str(title).strip():
        return jsonify({'error': 'Title is required'}), 400
    if not author or not str(author).strip():
        return jsonify({'error': 'Author is required'}), 400

    title = str(title).strip()
    author = str(author).strip()
    year = data.get('year', book['year'])
    isbn = data.get('isbn', book['isbn'])

    if year is not None:
        try:
            year = int(year)
        except (ValueError, TypeError):
            return jsonify({'error': 'Year must be an integer'}), 400

    db.execute(
        'UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?',
        (title, author, year, isbn, book_id)
    )
    db.commit()

    book = db.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()
    return jsonify(book_to_dict(book)), 200


@app.route('/books/<int:book_id>', methods=['DELETE'])
def delete_book(book_id):
    """Delete a book."""
    db = get_db()
    book = db.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()
    if book is None:
        return jsonify({'error': 'Book not found'}), 404

    db.execute('DELETE FROM books WHERE id = ?', (book_id,))
    db.commit()
    return jsonify({'message': 'Book deleted successfully'}), 200


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
