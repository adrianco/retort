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
    return g.db


@app.teardown_appcontext
def close_db(exception):
    """Close the database connection at the end of each request."""
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


def row_to_dict(row):
    """Convert a sqlite3.Row to a plain dict."""
    return dict(row)


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "healthy"}), 200


@app.route('/books', methods=['POST'])
def create_book():
    """Create a new book."""
    data = request.get_json()

    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    title = data.get('title')
    author = data.get('author')
    year = data.get('year')
    isbn = data.get('isbn')

    # Validate required fields
    if not title or not str(title).strip():
        return jsonify({"error": "title is required"}), 400
    if not author or not str(author).strip():
        return jsonify({"error": "author is required"}), 400

    title = str(title).strip()
    author = str(author).strip()

    # Validate year if provided
    if year is not None:
        try:
            year = int(year)
        except (ValueError, TypeError):
            return jsonify({"error": "year must be an integer"}), 400

    db = get_db()
    try:
        cursor = db.execute(
            'INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)',
            (title, author, year if year else None, isbn)
        )
        db.commit()
        book_id = cursor.lastrowid

        # Fetch the created book
        book = db.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()
        return jsonify(row_to_dict(book)), 201
    except sqlite3.IntegrityError:
        return jsonify({"error": "A book with this ISBN already exists"}), 409


@app.route('/books', methods=['GET'])
def list_books():
    """List all books, optionally filtered by author."""
    db = get_db()
    author_filter = request.args.get('author')

    if author_filter:
        books = db.execute(
            'SELECT * FROM books WHERE author LIKE ?',
            (f'%{author_filter}%',)
        ).fetchall()
    else:
        books = db.execute('SELECT * FROM books').fetchall()

    return jsonify([row_to_dict(b) for b in books]), 200


@app.route('/books/<int:book_id>', methods=['GET'])
def get_book(book_id):
    """Get a single book by ID."""
    db = get_db()
    book = db.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()

    if book is None:
        return jsonify({"error": "Book not found"}), 404

    return jsonify(row_to_dict(book)), 200


@app.route('/books/<int:book_id>', methods=['PUT'])
def update_book(book_id):
    """Update a book."""
    db = get_db()
    book = db.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()

    if book is None:
        return jsonify({"error": "Book not found"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    title = data.get('title', book['title'])
    author = data.get('author', book['author'])
    year = data.get('year', book['year'])
    isbn = data.get('isbn', book['isbn'])

    # Validate required fields
    if not title or not str(title).strip():
        return jsonify({"error": "title is required"}), 400
    if not author or not str(author).strip():
        return jsonify({"error": "author is required"}), 400

    title = str(title).strip()
    author = str(author).strip()

    # Validate year if provided
    if year is not None:
        try:
            year = int(year)
        except (ValueError, TypeError):
            return jsonify({"error": "year must be an integer"}), 400

    try:
        db.execute(
            'UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?',
            (title, author, year if year else None, isbn, book_id)
        )
        db.commit()

        # Fetch the updated book
        updated_book = db.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()
        return jsonify(row_to_dict(updated_book)), 200
    except sqlite3.IntegrityError:
        return jsonify({"error": "A book with this ISBN already exists"}), 409


@app.route('/books/<int:book_id>', methods=['DELETE'])
def delete_book(book_id):
    """Delete a book."""
    db = get_db()
    book = db.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()

    if book is None:
        return jsonify({"error": "Book not found"}), 404

    db.execute('DELETE FROM books WHERE id = ?', (book_id,))
    db.commit()

    return jsonify({"message": "Book deleted successfully"}), 200


# Initialize the database on import
init_db()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
