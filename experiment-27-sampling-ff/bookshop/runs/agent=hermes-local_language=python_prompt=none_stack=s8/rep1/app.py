"""Book API REST Service - CRUD operations for managing a book collection."""

import sqlite3
import os
from flask import Flask, request, jsonify, g

app = Flask(__name__)

DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'books.db')


def get_db():
    """Get database connection for current request."""
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
    db = sqlite3.connect(DATABASE)
    db.execute('''
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER,
            isbn TEXT UNIQUE
        )
    ''')
    db.commit()
    db.close()


def book_to_dict(book):
    """Convert a sqlite3.Row to a dictionary."""
    return {
        'id': book['id'],
        'title': book['title'],
        'author': book['author'],
        'year': book['year'],
        'isbn': book['isbn']
    }


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({'status': 'healthy'}), 200


@app.route('/books', methods=['POST'])
def create_book():
    """Create a new book."""
    data = request.get_json(silent=True) or {}

    if not data:
        return jsonify({'error': 'Request body must be JSON'}), 400

    title = data.get('title')
    author = data.get('author')
    year = data.get('year')
    isbn = data.get('isbn')

    # Validate required fields
    if not title or not str(title).strip():
        return jsonify({'error': 'Title is required'}), 400

    if not author or not str(author).strip():
        return jsonify({'error': 'Author is required'}), 400

    # Validate year if provided
    if year is not None:
        try:
            year = int(year)
            if year < 0 or year > 2100:
                return jsonify({'error': 'Year must be between 0 and 2100'}), 400
        except (ValueError, TypeError):
            return jsonify({'error': 'Year must be a valid integer'}), 400

    db = get_db()
    try:
        cursor = db.execute(
            'INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)',
            (str(title).strip(), str(author).strip(), year, isbn)
        )
        db.commit()
        book_id = cursor.lastrowid

        # Fetch the created book to return it
        new_book = db.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()
        return jsonify(book_to_dict(new_book)), 201
    except sqlite3.IntegrityError:
        return jsonify({'error': 'A book with this ISBN already exists'}), 409


@app.route('/books', methods=['GET'])
def list_books():
    """List all books with optional author filter."""
    db = get_db()
    author_filter = request.args.get('author')

    if author_filter:
        books = db.execute(
            'SELECT * FROM books WHERE author LIKE ?',
            (f'%{author_filter}%',)
        ).fetchall()
    else:
        books = db.execute('SELECT * FROM books').fetchall()

    return jsonify([book_to_dict(book) for book in books]), 200


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
    existing_book = db.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()

    if existing_book is None:
        return jsonify({'error': 'Book not found'}), 404

    data = request.get_json(silent=True) or {}
    if not data:
        return jsonify({'error': 'Request body must be JSON'}), 400

    title = data.get('title', existing_book['title'])
    author = data.get('author', existing_book['author'])
    year = data.get('year', existing_book['year'])
    isbn = data.get('isbn', existing_book['isbn'])

    # Validate required fields if provided
    if not title or not str(title).strip():
        return jsonify({'error': 'Title is required'}), 400

    if not author or not str(author).strip():
        return jsonify({'error': 'Author is required'}), 400

    # Validate year if provided
    if year is not None:
        try:
            year = int(year)
            if year < 0 or year > 2100:
                return jsonify({'error': 'Year must be between 0 and 2100'}), 400
        except (ValueError, TypeError):
            return jsonify({'error': 'Year must be a valid integer'}), 400

    try:
        db.execute(
            'UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?',
            (str(title).strip(), str(author).strip(), year, isbn, book_id)
        )
        db.commit()

        updated_book = db.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()
        return jsonify(book_to_dict(updated_book)), 200
    except sqlite3.IntegrityError:
        return jsonify({'error': 'A book with this ISBN already exists'}), 409


@app.route('/books/<int:book_id>', methods=['DELETE'])
def delete_book(book_id):
    """Delete a book."""
    db = get_db()
    existing_book = db.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()

    if existing_book is None:
        return jsonify({'error': 'Book not found'}), 404

    db.execute('DELETE FROM books WHERE id = ?', (book_id,))
    db.commit()

    return jsonify({'message': 'Book deleted successfully'}), 200


# Initialize the database when the module is loaded
init_db()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
