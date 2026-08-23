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
    """Initialize the database with the books table."""
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


def row_to_dict(row):
    """Convert a sqlite3.Row to a plain dict."""
    return dict(row)


@app.route('/health', methods=['GET'])
def health():
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
    year = data.get('year')
    isbn = data.get('isbn')

    if not title or not str(title).strip():
        return jsonify({'error': 'title is required'}), 400
    if not author or not str(author).strip():
        return jsonify({'error': 'author is required'}), 400

    title = str(title).strip()
    author = str(author).strip()

    db = get_db()
    cursor = db.execute(
        'INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)',
        (title, author, year, isbn)
    )
    db.commit()
    book_id = cursor.lastrowid

    book = get_book_by_id(book_id)
    return jsonify(book), 201


@app.route('/books', methods=['GET'])
def list_books():
    """List all books, optionally filtered by author."""
    db = get_db()
    author_filter = request.args.get('author')

    if author_filter:
        rows = db.execute(
            'SELECT * FROM books WHERE author LIKE ?',
            (f'%{author_filter}%',)
        ).fetchall()
    else:
        rows = db.execute('SELECT * FROM books').fetchall()

    books = [row_to_dict(row) for row in rows]
    return jsonify(books), 200


@app.route('/books/<int:book_id>', methods=['GET'])
def get_book(book_id):
    """Get a single book by ID."""
    book = get_book_by_id(book_id)
    if book is None:
        return jsonify({'error': 'Book not found'}), 404
    return jsonify(book), 200


@app.route('/books/<int:book_id>', methods=['PUT'])
def update_book(book_id):
    """Update a book."""
    existing = get_book_by_id(book_id)
    if existing is None:
        return jsonify({'error': 'Book not found'}), 404

    data = request.get_json()
    if not data:
        return jsonify({'error': 'Request body must be JSON'}), 400

    title = data.get('title', existing['title'])
    author = data.get('author', existing['author'])
    year = data.get('year', existing['year'])
    isbn = data.get('isbn', existing['isbn'])

    if not title or not str(title).strip():
        return jsonify({'error': 'title is required'}), 400
    if not author or not str(author).strip():
        return jsonify({'error': 'author is required'}), 400

    title = str(title).strip()
    author = str(author).strip()

    db = get_db()
    db.execute(
        'UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?',
        (title, author, year, isbn, book_id)
    )
    db.commit()

    book = get_book_by_id(book_id)
    return jsonify(book), 200


@app.route('/books/<int:book_id>', methods=['DELETE'])
def delete_book(book_id):
    """Delete a book."""
    existing = get_book_by_id(book_id)
    if existing is None:
        return jsonify({'error': 'Book not found'}), 404

    db = get_db()
    db.execute('DELETE FROM books WHERE id = ?', (book_id,))
    db.commit()

    return jsonify({'message': 'Book deleted'}), 200


def get_book_by_id(book_id):
    """Retrieve a single book by ID."""
    db = get_db()
    row = db.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()
    if row is None:
        return None
    return row_to_dict(row)


# Initialize the database on import
init_db()


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
