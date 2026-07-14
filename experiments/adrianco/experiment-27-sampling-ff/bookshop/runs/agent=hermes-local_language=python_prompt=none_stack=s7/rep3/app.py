import sqlite3
import os
from flask import Flask, request, jsonify, g

DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'books.db')


def get_db():
    """Get a database connection for the current request."""
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA journal_mode=WAL")
    return g.db


def teardown_db(exception):
    """Close the database connection at the end of the request."""
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db(db_path=None):
    """Initialize the database with the books table."""
    path = db_path or DATABASE
    db = sqlite3.connect(path)
    db.execute("""
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER,
            isbn TEXT
        )
    """)
    db.commit()
    db.close()


def create_app(test_db_path=None):
    """Application factory."""
    global DATABASE
    app = Flask(__name__)

    if test_db_path:
        DATABASE = test_db_path

    app.add_url_rule('/health', 'health_check', health_check, methods=['GET'])
    app.add_url_rule('/books', 'list_books', list_books, methods=['GET'])
    app.add_url_rule('/books', 'create_book', create_book, methods=['POST'])
    app.add_url_rule('/books/<int:book_id>', 'get_book', get_book, methods=['GET'])
    app.add_url_rule('/books/<int:book_id>', 'update_book', update_book, methods=['PUT'])
    app.add_url_rule('/books/<int:book_id>', 'delete_book', delete_book, methods=['DELETE'])

    app.teardown_appcontext(teardown_db)

    init_db()

    return app


def health_check():
    """Health check endpoint."""
    return jsonify({"status": "healthy"}), 200


def create_book():
    """Create a new book."""
    data = request.get_json()

    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    title = data.get('title')
    author = data.get('author')
    year = data.get('year')
    isbn = data.get('isbn')

    if not title or not str(title).strip():
        return jsonify({"error": "Title is required"}), 400

    if not author or not str(author).strip():
        return jsonify({"error": "Author is required"}), 400

    db = get_db()
    cursor = db.execute(
        "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
        (str(title).strip(), str(author).strip(), year, isbn)
    )
    db.commit()

    book_id = cursor.lastrowid

    return jsonify({
        "id": book_id,
        "title": title.strip(),
        "author": author.strip(),
        "year": year,
        "isbn": isbn
    }), 201


def list_books():
    """List all books, optionally filtered by author."""
    author_filter = request.args.get('author')

    db = get_db()

    if author_filter:
        cursor = db.execute(
            "SELECT * FROM books WHERE author LIKE ?",
            ("%" + author_filter + "%",)
        )
    else:
        cursor = db.execute("SELECT * FROM books")

    books = [
        {
            "id": row["id"],
            "title": row["title"],
            "author": row["author"],
            "year": row["year"],
            "isbn": row["isbn"]
        }
        for row in cursor.fetchall()
    ]

    return jsonify(books), 200


def get_book(book_id):
    """Get a single book by ID."""
    db = get_db()
    cursor = db.execute("SELECT * FROM books WHERE id = ?", (book_id,))
    row = cursor.fetchone()

    if row is None:
        return jsonify({"error": "Book not found"}), 404

    return jsonify({
        "id": row["id"],
        "title": row["title"],
        "author": row["author"],
        "year": row["year"],
        "isbn": row["isbn"]
    }), 200


def update_book(book_id):
    """Update a book."""
    db = get_db()
    cursor = db.execute("SELECT * FROM books WHERE id = ?", (book_id,))
    row = cursor.fetchone()

    if row is None:
        return jsonify({"error": "Book not found"}), 404

    data = request.get_json()

    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    title = data.get('title', row['title'])
    author = data.get('author', row['author'])
    year = data.get('year', row['year'])
    isbn = data.get('isbn', row['isbn'])

    if not title or not str(title).strip():
        return jsonify({"error": "Title is required"}), 400

    if not author or not str(author).strip():
        return jsonify({"error": "Author is required"}), 400

    db.execute(
        "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?",
        (str(title).strip(), str(author).strip(), year, isbn, book_id)
    )
    db.commit()

    return jsonify({
        "id": book_id,
        "title": title.strip(),
        "author": author.strip(),
        "year": year,
        "isbn": isbn
    }), 200


def delete_book(book_id):
    """Delete a book."""
    db = get_db()
    cursor = db.execute("SELECT * FROM books WHERE id = ?", (book_id,))
    row = cursor.fetchone()

    if row is None:
        return jsonify({"error": "Book not found"}), 404

    db.execute("DELETE FROM books WHERE id = ?", (book_id,))
    db.commit()

    return jsonify({"message": "Book deleted successfully"}), 200



if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)
