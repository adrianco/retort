import sqlite3
import os
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
    """Initialize the database and create the books table if it doesn't exist."""
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
    """Create a new book.

    Expected JSON body:
    {
        "title": "Book Title",
        "author": "Author Name",
        "year": 2024,
        "isbn": "978-3-16-148410-0"
    }

    Returns:
    - 201 Created with the book data on success
    - 400 Bad Request if title or author is missing
    """
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

    db = get_db()
    cursor = db.execute(
        'INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)',
        (str(title).strip(), str(author).strip(), year, isbn)
    )
    db.commit()

    new_book = db.execute('SELECT * FROM books WHERE id = ?', (cursor.lastrowid,)).fetchone()
    return jsonify(book_to_dict(new_book)), 201


@app.route('/books', methods=['GET'])
def list_books():
    """List all books, with optional ?author= filter.

    Query parameters:
    - author (optional): Filter books by author name (case-insensitive partial match)

    Returns:
    - 200 OK with a list of books
    """
    author_filter = request.args.get('author')

    db = get_db()

    if author_filter:
        books = db.execute(
            'SELECT * FROM books WHERE LOWER(author) LIKE LOWER(?)',
            (f'%{author_filter}%',)
        ).fetchall()
    else:
        books = db.execute('SELECT * FROM books').fetchall()

    return jsonify([book_to_dict(book) for book in books]), 200


@app.route('/books/<int:book_id>', methods=['GET'])
def get_book(book_id):
    """Get a single book by ID.

    Returns:
    - 200 OK with the book data on success
    - 404 Not Found if the book doesn't exist
    """
    db = get_db()
    book = db.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()

    if book is None:
        return jsonify({'error': 'Book not found'}), 404

    return jsonify(book_to_dict(book)), 200


@app.route('/books/<int:book_id>', methods=['PUT'])
def update_book(book_id):
    """Update a book by ID.

    Expected JSON body (all fields optional):
    {
        "title": "New Title",
        "author": "New Author",
        "year": 2025,
        "isbn": "978-3-16-148410-1"
    }

    Returns:
    - 200 OK with the updated book data on success
    - 404 Not Found if the book doesn't exist
    - 400 Bad Request if title or author is provided but empty
    """
    db = get_db()
    book = db.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()

    if book is None:
        return jsonify({'error': 'Book not found'}), 404

    data = request.get_json()

    if not data:
        return jsonify({'error': 'Request body must be JSON'}), 400

    title = data.get('title', book['title'])
    author = data.get('author', book['author'])
    year = data.get('year', book['year'])
    isbn = data.get('isbn', book['isbn'])

    if not str(title).strip():
        return jsonify({'error': 'Title is required'}), 400

    if not str(author).strip():
        return jsonify({'error': 'Author is required'}), 400

    db.execute(
        'UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?',
        (str(title).strip(), str(author).strip(), year, isbn, book_id)
    )
    db.commit()

    updated_book = db.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()
    return jsonify(book_to_dict(updated_book)), 200


@app.route('/books/<int:book_id>', methods=['DELETE'])
def delete_book(book_id):
    """Delete a book by ID.

    Returns:
    - 200 OK with a success message on success
    - 404 Not Found if the book doesn't exist
    """
    db = get_db()
    book = db.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()

    if book is None:
        return jsonify({'error': 'Book not found'}), 404

    db.execute('DELETE FROM books WHERE id = ?', (book_id,))
    db.commit()

    return jsonify({'message': 'Book deleted successfully'}), 200


# Initialize the database on import (for testing and direct execution)
init_db()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
