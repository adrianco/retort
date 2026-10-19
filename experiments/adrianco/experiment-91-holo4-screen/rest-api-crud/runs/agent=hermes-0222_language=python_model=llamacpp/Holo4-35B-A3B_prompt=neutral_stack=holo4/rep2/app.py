import sqlite3
import json
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


def book_to_dict(row):
    """Convert a database row to a dictionary."""
    return {
        'id': row['id'],
        'title': row['title'],
        'author': row['author'],
        'year': row['year'],
        'isbn': row['isbn']
    }


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

    book = {
        'id': cursor.lastrowid,
        'title': title.strip(),
        'author': author.strip(),
        'year': year,
        'isbn': isbn
    }
    return jsonify(book), 201


@app.route('/books', methods=['GET'])
def list_books():
    """List all books, with optional author filter."""
    author = request.args.get('author')
    db = get_db()

    if author:
        rows = db.execute('SELECT * FROM books WHERE author = ?', (author,)).fetchall()
    else:
        rows = db.execute('SELECT * FROM books').fetchall()

    books = [book_to_dict(row) for row in rows]
    return jsonify(books), 200


@app.route('/books/<int:id>', methods=['GET'])
def get_book(id):
    """Get a single book by ID."""
    db = get_db()
    row = db.execute('SELECT * FROM books WHERE id = ?', (id,)).fetchone()
    if row is None:
        return jsonify({'error': 'Book not found'}), 404
    return jsonify(book_to_dict(row)), 200


@app.route('/books/<int:id>', methods=['PUT'])
def update_book(id):
    """Update a book."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Request body must be JSON'}), 400

    db = get_db()
    row = db.execute('SELECT * FROM books WHERE id = ?', (id,)).fetchone()
    if row is None:
        return jsonify({'error': 'Book not found'}), 404

    title = data.get('title', row['title'])
    author = data.get('author', row['author'])

    if not title or not title.strip():
        return jsonify({'error': 'Title is required'}), 400
    if not author or not author.strip():
        return jsonify({'error': 'Author is required'}), 400

    year = data.get('year', row['year'])
    isbn = data.get('isbn', row['isbn'])

    db.execute(
        'UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?',
        (title.strip(), author.strip(), year, isbn, id)
    )
    db.commit()

    updated = db.execute('SELECT * FROM books WHERE id = ?', (id,)).fetchone()
    return jsonify(book_to_dict(updated)), 200


@app.route('/books/<int:id>', methods=['DELETE'])
def delete_book(id):
    """Delete a book."""
    db = get_db()
    row = db.execute('SELECT * FROM books WHERE id = ?', (id,)).fetchone()
    if row is None:
        return jsonify({'error': 'Book not found'}), 404

    db.execute('DELETE FROM books WHERE id = ?', (id,))
    db.commit()
    return '', 204


# Initialize the database when the module loads
init_db()

if __name__ == '__main__':
    app.run(debug=True, port=5000)
