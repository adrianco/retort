"""Book Collection REST API Service."""

import sqlite3
from datetime import datetime, timezone
from flask import Flask, request, jsonify, g

app = Flask(__name__)
DATABASE = 'books.db'


def get_db():
    """Get database connection for current request context."""
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db


@app.teardown_appcontext
def close_connection(exception):
    """Close database connection at end of request."""
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


def init_db():
    """Initialize database schema."""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER,
            isbn TEXT,
            created_at TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()


def validate_book_data(data, require_all=True):
    """Validate book data."""
    errors = []
    if require_all:
        if not data.get('title') or not isinstance(data.get('title'), str) or not data.get('title').strip():
            errors.append('Title is required')
        if not data.get('author') or not isinstance(data.get('author'), str) or not data.get('author').strip():
            errors.append('Author is required')
    else:
        if 'title' in data and (not isinstance(data.get('title'), str) or not data.get('title').strip()):
            errors.append('Title must be a non-empty string')
        if 'author' in data and (not isinstance(data.get('author'), str) or not data.get('author').strip()):
            errors.append('Author must be a non-empty string')
    
    if 'year' in data and data.get('year') is not None:
        try:
            year = int(data['year'])
            if year < 0 or year > 9999:
                errors.append('Year must be a valid year (0-9999)')
        except (ValueError, TypeError):
            errors.append('Year must be a valid integer')
    
    if 'isbn' in data and data.get('isbn') is not None:
        if not isinstance(data['isbn'], str):
            errors.append('ISBN must be a string')
    
    return errors


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now(timezone.utc).isoformat()}), 200


@app.route('/books', methods=['POST'])
def create_book():
    """Create a new book."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Request body is required'}), 400
    
    errors = validate_book_data(data, require_all=True)
    if errors:
        return jsonify({'error': errors}), 400
    
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        'INSERT INTO books (title, author, year, isbn, created_at) VALUES (?, ?, ?, ?, ?)',
        (data['title'].strip(), data['author'].strip(), 
         data.get('year'), data.get('isbn'), datetime.now(timezone.utc).isoformat())
    )
    db.commit()
    
    book_id = cursor.lastrowid
    cursor.execute('SELECT * FROM books WHERE id = ?', (book_id,))
    book = cursor.fetchone()
    db.close()
    
    return jsonify(dict(book)), 201


@app.route('/books', methods=['GET'])
def list_books():
    """List all books with optional author filter."""
    author = request.args.get('author')
    db = get_db()
    cursor = db.cursor()
    
    if author:
        cursor.execute('SELECT * FROM books WHERE author LIKE ?', (f'%{author}%',))
    else:
        cursor.execute('SELECT * FROM books')
    
    books = [dict(row) for row in cursor.fetchall()]
    db.close()
    
    return jsonify(books), 200


@app.route('/books/<int:book_id>', methods=['GET'])
def get_book(book_id):
    """Get a single book by ID."""
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM books WHERE id = ?', (book_id,))
    book = cursor.fetchone()
    db.close()
    
    if not book:
        return jsonify({'error': 'Book not found'}), 404
    
    return jsonify(dict(book)), 200


@app.route('/books/<int:book_id>', methods=['PUT'])
def update_book(book_id):
    """Update a book."""
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM books WHERE id = ?', (book_id,))
    existing_book = cursor.fetchone()
    
    if not existing_book:
        db.close()
        return jsonify({'error': 'Book not found'}), 404
    
    data = request.get_json()
    if not data:
        db.close()
        return jsonify({'error': 'Request body is required'}), 400
    
    errors = validate_book_data(data, require_all=False)
    if errors:
        db.close()
        return jsonify({'error': errors}), 400
    
    # Build update query dynamically
    updates = []
    values = []
    if 'title' in data:
        updates.append('title = ?')
        values.append(data['title'].strip())
    if 'author' in data:
        updates.append('author = ?')
        values.append(data['author'].strip())
    if 'year' in data:
        updates.append('year = ?')
        values.append(data['year'])
    if 'isbn' in data:
        updates.append('isbn = ?')
        values.append(data['isbn'])
    
    if updates:
        values.append(book_id)
        query = f'UPDATE books SET {", ".join(updates)} WHERE id = ?'
        cursor.execute(query, values)
        db.commit()
    
    cursor.execute('SELECT * FROM books WHERE id = ?', (book_id,))
    book = cursor.fetchone()
    db.close()
    
    return jsonify(dict(book)), 200


@app.route('/books/<int:book_id>', methods=['DELETE'])
def delete_book(book_id):
    """Delete a book."""
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM books WHERE id = ?', (book_id,))
    existing_book = cursor.fetchone()
    
    if not existing_book:
        db.close()
        return jsonify({'error': 'Book not found'}), 404
    
    cursor.execute('DELETE FROM books WHERE id = ?', (book_id,))
    db.commit()
    db.close()
    
    return jsonify({'message': 'Book deleted successfully'}), 200


if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)
