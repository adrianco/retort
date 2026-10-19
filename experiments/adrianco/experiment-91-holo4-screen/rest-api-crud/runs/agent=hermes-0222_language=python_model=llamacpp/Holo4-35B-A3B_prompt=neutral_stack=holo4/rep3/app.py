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
        _ensure_table(g.db)
    return g.db


def _ensure_table(db):
    """Create the books table if it doesn't exist."""
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


@app.teardown_appcontext
def close_db(exception):
    """Close database connection at end of request."""
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    """Initialize the database and create the books table if it doesn't exist."""
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


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({'status': 'ok'}), 200


@app.route('/books', methods=['POST'])
def create_book():
    """Create a new book."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Request body must be JSON'}), 400

    title = data.get('title')
    author = data.get('author')

    if not title or not title.strip():
        return jsonify({'error': 'Title is required'}), 400
    if not author or not author.strip():
        return jsonify({'error': 'Author is required'}), 400

    year = data.get('year')
    isbn = data.get('isbn')

    db = get_db()
    cursor = db.execute(
        'INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)',
        (title.strip(), author.strip(), year, isbn)
    )
    db.commit()
    book_id = cursor.lastrowid

    return jsonify({
        'id': book_id,
        'title': title.strip(),
        'author': author.strip(),
        'year': year,
        'isbn': isbn
    }), 201


@app.route('/books', methods=['GET'])
def list_books():
    """List all books, optionally filtered by author."""
    author = request.args.get('author')
    db = get_db()

    if author:
        books = db.execute(
            'SELECT id, title, author, year, isbn FROM books WHERE author = ?',
            (author,)
        ).fetchall()
    else:
        books = db.execute(
            'SELECT id, title, author, year, isbn FROM books'
        ).fetchall()

    return jsonify([dict(book) for book in books]), 200


@app.route('/books/<int:book_id>', methods=['GET'])
def get_book(book_id):
    """Get a single book by ID."""
    db = get_db()
    book = db.execute(
        'SELECT id, title, author, year, isbn FROM books WHERE id = ?',
        (book_id,)
    ).fetchone()

    if book is None:
        return jsonify({'error': 'Book not found'}), 404

    return jsonify(dict(book)), 200


@app.route('/books/<int:book_id>', methods=['PUT'])
def update_book(book_id):
    """Update a book."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Request body must be JSON'}), 400

    db = get_db()
    book = db.execute(
        'SELECT id, title, author, year, isbn FROM books WHERE id = ?',
        (book_id,)
    ).fetchone()

    if book is None:
        return jsonify({'error': 'Book not found'}), 404

    title = data.get('title', book['title'])
    author = data.get('author', book['author'])
    year = data.get('year', book['year'])
    isbn = data.get('isbn', book['isbn'])

    if not title or not title.strip():
        return jsonify({'error': 'Title is required'}), 400
    if not author or not author.strip():
        return jsonify({'error': 'Author is required'}), 400

    db.execute(
        'UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?',
        (title.strip(), author.strip(), year, isbn, book_id)
    )
    db.commit()

    return jsonify({
        'id': book_id,
        'title': title.strip(),
        'author': author.strip(),
        'year': year,
        'isbn': isbn
    }), 200


@app.route('/books/<int:book_id>', methods=['DELETE'])
def delete_book(book_id):
    """Delete a book."""
    db = get_db()
    book = db.execute(
        'SELECT id FROM books WHERE id = ?', (book_id,)
    ).fetchone()

    if book is None:
        return jsonify({'error': 'Book not found'}), 404

    db.execute('DELETE FROM books WHERE id = ?', (book_id,))
    db.commit()

    return jsonify({'message': 'Book deleted'}), 200


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
