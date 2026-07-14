"""Book API REST Service - Flask application with SQLite storage."""

import sqlite3
import os
from flask import Flask, request, jsonify, g

DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'books.db')


def create_app(database_path=None):
    """Create and configure the Flask application."""
    app = Flask(__name__)

    if database_path is None:
        database_path = DATABASE

    # For in-memory databases, store the connection on the app object
    if database_path == ':memory:':
        _db_conn = sqlite3.connect(database_path)
        _db_conn.row_factory = sqlite3.Row
    else:
        _db_conn = None

    def get_db():
        """Get database connection for current request."""
        if _db_conn is not None:
            # In-memory DB: use the shared connection stored on app
            return _db_conn
        if 'db' not in g:
            g.db = sqlite3.connect(database_path)
            g.db.row_factory = sqlite3.Row
        return g.db

    @app.teardown_appcontext
    def close_db(exception):
        """Close database connection at end of request."""
        if _db_conn is not None:
            # Don't close in-memory DB; it's shared across requests
            return
        db = g.pop('db', None)
        if db is not None:
            db.close()

    def init_db():
        """Initialize the database with the books table."""
        if _db_conn is not None:
            # In-memory DB: use the shared connection directly (no g context needed)
            _db_conn.execute('''
                CREATE TABLE IF NOT EXISTS books (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    author TEXT NOT NULL,
                    year INTEGER,
                    isbn TEXT
                )
            ''')
            _db_conn.commit()
        else:
            # File-based DB: create connection directly (no g context at import time)
            db = sqlite3.connect(database_path)
            db.row_factory = sqlite3.Row
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
        """Convert a sqlite3.Row to a dictionary."""
        if row is None:
            return None
        return dict(row)

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

        db = get_db()
        cursor = db.execute(
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
        author_filter = request.args.get('author')

        if author_filter:
            books = db.execute(
                'SELECT * FROM books WHERE author LIKE ?',
                (f'%{author_filter}%',)
            ).fetchall()
        else:
            books = db.execute('SELECT * FROM books').fetchall()

        return jsonify([row_to_dict(book) for book in books]), 200

    @app.route('/books/<int:book_id>', methods=['GET'])
    def get_book(book_id):
        """Get a single book by ID."""
        db = get_db()
        book = db.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()

        if book is None:
            return jsonify({'error': 'Book not found'}), 404

        return jsonify(row_to_dict(book)), 200

    @app.route('/books/<int:book_id>', methods=['PUT'])
    def update_book(book_id):
        """Update a book."""
        db = get_db()
        existing_book = db.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()

        if existing_book is None:
            return jsonify({'error': 'Book not found'}), 404

        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body must be JSON'}), 400

        title = data.get('title', existing_book['title'])
        author = data.get('author', existing_book['author'])

        if not title or not str(title).strip():
            return jsonify({'error': 'Title is required'}), 400

        if not author or not str(author).strip():
            return jsonify({'error': 'Author is required'}), 400

        year = data.get('year', existing_book['year'])
        isbn = data.get('isbn', existing_book['isbn'])

        db.execute(
            'UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?',
            (str(title).strip(), str(author).strip(), year, isbn, book_id)
        )
        db.commit()

        updated_book = db.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()

        return jsonify(row_to_dict(updated_book)), 200

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

    # Initialize database
    init_db()

    return app


# Create the default application instance for running directly
app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
