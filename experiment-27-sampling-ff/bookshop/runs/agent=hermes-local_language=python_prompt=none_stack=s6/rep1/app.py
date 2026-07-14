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


def book_to_dict(row):
    """Convert a sqlite3.Row to a dictionary."""
    return {
        'id': row['id'],
        'title': row['title'],
        'author': row['author'],
        'year': row['year'],
        'isbn': row['isbn']
    }


def validate_book_data(data, required_fields=None):
    """Validate book data. Returns (errors_dict, is_valid)."""
    if required_fields is None:
        required_fields = ['title', 'author']
    errors = {}
    if not data:
        return {'error': 'Request body is required'}, False
    for field in required_fields:
        value = data.get(field)
        if value is None or (isinstance(value, str) and value.strip() == ''):
            errors[field] = f'{field} is required'
    # Validate year if provided
    if 'year' in data and data['year'] is not None:
        try:
            year_val = int(data['year'])
            if year_val < 0 or year_val > 2100:
                errors['year'] = 'Year must be between 0 and 2100'
        except (ValueError, TypeError):
            errors['year'] = 'Year must be a valid integer'
    return errors, len(errors) == 0


@app.before_request
def ensure_tables():
    """Ensure the database tables exist before each request."""
    init_db()


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({'status': 'healthy'}), 200


@app.route('/books', methods=['POST'])
def create_book():
    """Create a new book."""
    data = request.get_json()
    errors, is_valid = validate_book_data(data)
    if not is_valid:
        return jsonify(errors), 400

    db = get_db()
    cursor = db.execute(
        'INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)',
        (data['title'].strip(), data['author'].strip(),
         int(data.get('year')) if data.get('year') else None,
         data.get('isbn', '').strip() if data.get('isbn') else None)
    )
    db.commit()
    book_id = cursor.lastrowid

    book = db.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()
    return jsonify(book_to_dict(book)), 201


@app.route('/books', methods=['GET'])
def list_books():
    """List all books, with optional author filter."""
    db = get_db()
    query = 'SELECT * FROM books'
    params = []

    author = request.args.get('author')
    if author:
        query += ' WHERE author LIKE ?'
        params.append(f'%{author}%')

    books = db.execute(query, params).fetchall()
    return jsonify([book_to_dict(b) for b in books]), 200


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
    book = db.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()
    if book is None:
        return jsonify({'error': 'Book not found'}), 404

    data = request.get_json()
    if not data:
        return jsonify({'error': 'Request body is required'}), 400

    # Validate required fields if title or author are being updated
    errors, is_valid = validate_book_data(data, required_fields=[])
    if 'title' in data:
        if data['title'] is None or (isinstance(data['title'], str) and data['title'].strip() == ''):
            errors['title'] = 'title is required'
    if 'author' in data:
        if data['author'] is None or (isinstance(data['author'], str) and data['author'].strip() == ''):
            errors['author'] = 'author is required'
    if errors:
        return jsonify(errors), 400

    # Validate year if provided
    if 'year' in data and data['year'] is not None:
        try:
            year_val = int(data['year'])
            if year_val < 0 or year_val > 2100:
                return jsonify({'year': 'Year must be between 0 and 2100'}), 400
        except (ValueError, TypeError):
            return jsonify({'year': 'Year must be a valid integer'}), 400

    title = data.get('title', book['title']).strip()
    author = data.get('author', book['author']).strip()
    year = int(data['year']) if 'year' in data and data['year'] is not None else book['year']
    isbn = data.get('isbn', book['isbn'])
    if isbn:
        isbn = isbn.strip()
    else:
        isbn = None

    db.execute(
        'UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?',
        (title, author, year, isbn, book_id)
    )
    db.commit()

    updated_book = db.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()
    return jsonify(book_to_dict(updated_book)), 200


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


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
