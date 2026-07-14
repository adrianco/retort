import sqlite3
import os
from flask import Flask, request, jsonify, g

app = Flask(__name__)

DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'books.db')


def get_db():
    """Get a database connection for the current request."""
    if 'db' not in g:
        db_path = getattr(app, '_test_db_path', DATABASE)
        g.db = sqlite3.connect(db_path)
        g.db.row_factory = sqlite3.Row
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

    if not title or not isinstance(title, str) or title.strip() == '':
        return jsonify({'error': 'Title is required and must be a non-empty string'}), 400

    if not author or not isinstance(author, str) or author.strip() == '':
        return jsonify({'error': 'Author is required and must be a non-empty string'}), 400

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
    """List all books, with optional author filter."""
    db = get_db()
    author = request.args.get('author')

    if author:
        books = db.execute(
            'SELECT * FROM books WHERE author = ?', (author,)
        ).fetchall()
    else:
        books = db.execute('SELECT * FROM books').fetchall()

    result = []
    for book in books:
        result.append({
            'id': book['id'],
            'title': book['title'],
            'author': book['author'],
            'year': book['year'],
            'isbn': book['isbn']
        })

    return jsonify(result), 200


@app.route('/books/<int:book_id>', methods=['GET'])
def get_book(book_id):
    """Get a single book by ID."""
    db = get_db()
    book = db.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()

    if book is None:
        return jsonify({'error': 'Book not found'}), 404

    return jsonify({
        'id': book['id'],
        'title': book['title'],
        'author': book['author'],
        'year': book['year'],
        'isbn': book['isbn']
    }), 200


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
    year = data.get('year', book['year'])
    isbn = data.get('isbn', book['isbn'])

    if not isinstance(title, str) or title.strip() == '':
        return jsonify({'error': 'Title is required and must be a non-empty string'}), 400

    if not isinstance(author, str) or author.strip() == '':
        return jsonify({'error': 'Author is required and must be a non-empty string'}), 400

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
    book = db.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()

    if book is None:
        return jsonify({'error': 'Book not found'}), 404

    db.execute('DELETE FROM books WHERE id = ?', (book_id,))
    db.commit()

    return jsonify({'message': 'Book deleted successfully'}), 200


# Initialize the database on import
init_db()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
