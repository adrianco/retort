"""Book API REST Service."""
import os
import sqlite3
from flask import Flask, jsonify, request, g


def get_db():
    """Get database connection for current request."""
    if 'db' not in g:
        g.db = sqlite3.connect(os.environ.get('DATABASE_PATH', '/tmp/books.db'))
        g.db.row_factory = sqlite3.Row
    return g.db


def init_db():
    """Initialize the database schema."""
    db = sqlite3.connect(os.environ.get('DATABASE_PATH', '/tmp/books.db'))
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


def create_app(db_path=None):
    """Create and configure the Flask application."""
    if db_path:
        os.environ['DATABASE_PATH'] = db_path

    app = Flask(__name__)
    init_db()

    @app.route('/health', methods=['GET'])
    def health():
        """Health check endpoint."""
        return jsonify({"status": "ok"}), 200

    @app.route('/books', methods=['GET'])
    def list_books():
        """List all books, optionally filtered by author."""
        db = get_db()
        author = request.args.get('author')
        if author:
            books = db.execute(
                'SELECT * FROM books WHERE author LIKE ?',
                (f'%{author}%',)
            ).fetchall()
        else:
            books = db.execute('SELECT * FROM books').fetchall()
        return jsonify([dict(b) for b in books]), 200

    @app.route('/books', methods=['POST'])
    def create_book():
        """Create a new book."""
        data = request.get_json()
        if not data or not data.get('title'):
            return jsonify({"error": "title is required"}), 400
        if not data.get('author'):
            return jsonify({"error": "author is required"}), 400

        db = get_db()
        cursor = db.execute(
            'INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)',
            (data['title'], data['author'], data.get('year'), data.get('isbn'))
        )
        db.commit()
        book = db.execute('SELECT * FROM books WHERE id = ?', (cursor.lastrowid,)).fetchone()
        return jsonify(dict(book)), 201

    @app.route('/books/<int:book_id>', methods=['GET'])
    def get_book(book_id):
        """Get a single book by ID."""
        db = get_db()
        book = db.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()
        if book is None:
            return jsonify({"error": "Book not found"}), 404
        return jsonify(dict(book)), 200

    @app.route('/books/<int:book_id>', methods=['PUT'])
    def update_book(book_id):
        """Update a book."""
        db = get_db()
        book = db.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()
        if book is None:
            return jsonify({"error": "Book not found"}), 404

        data = request.get_json()
        title = data.get('title', book['title'])
        author = data.get('author', book['author'])
        year = data.get('year', book['year'])
        isbn = data.get('isbn', book['isbn'])

        if not title or not author:
            return jsonify({"error": "title and author are required"}), 400

        db.execute(
            'UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?',
            (title, author, year, isbn, book_id)
        )
        db.commit()
        book = db.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()
        return jsonify(dict(book)), 200

    @app.route('/books/<int:book_id>', methods=['DELETE'])
    def delete_book(book_id):
        """Delete a book."""
        db = get_db()
        book = db.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()
        if book is None:
            return jsonify({"error": "Book not found"}), 404

        db.execute('DELETE FROM books WHERE id = ?', (book_id,))
        db.commit()
        return jsonify({"message": "Book deleted"}), 200

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)
