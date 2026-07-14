"""
Book Collection REST API Service
"""
from flask import Flask, request, jsonify, g
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)

# Use environment variable for database or default
DATABASE = os.environ.get('DATABASE', 'books.db')


def get_db():
    """Get database connection for current request context."""
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


def validate_book(data, required_title=True, required_author=True):
    """Validate book data."""
    errors = []
    
    if required_title:
        if 'title' not in data or not data.get('title', '').strip():
            errors.append('Title is required')
        elif not isinstance(data['title'], str):
            errors.append('Title must be a string')
        elif not data['title'].strip():
            errors.append('Title cannot be empty')
    
    if required_author:
        if 'author' not in data or not data.get('author', '').strip():
            errors.append('Author is required')
        elif not isinstance(data['author'], str):
            errors.append('Author must be a string')
        elif not data['author'].strip():
            errors.append('Author cannot be empty')
    
    if 'year' in data and data['year'] is not None:
        try:
            year = int(data['year'])
            if year < 0 or year > 9999:
                errors.append('Year must be a valid year (0-9999)')
        except (ValueError, TypeError):
            errors.append('Year must be a valid integer')
    
    if 'isbn' in data and data['isbn'] is not None:
        if not isinstance(data['isbn'], str):
            errors.append('ISBN must be a string')
    
    return errors


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    try:
        db = get_db()
        db.execute('SELECT 1')
        return jsonify({'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()}), 200
    except Exception as e:
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 500


@app.route('/books', methods=['POST'])
def create_book():
    """Create a new book."""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'Request body is required'}), 400
    
    errors = validate_book(data)
    if errors:
        return jsonify({'error': errors}), 400
    
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        'INSERT INTO books (title, author, year, isbn, created_at) VALUES (?, ?, ?, ?, ?)',
        (
            data['title'].strip(),
            data['author'].strip(),
            data.get('year'),
            data.get('isbn'),
            datetime.utcnow().isoformat()
        )
    )
    db.commit()
    
    book_id = cursor.lastrowid
    cursor.execute('SELECT * FROM books WHERE id = ?', (book_id,))
    book = cursor.fetchone()
    
    return jsonify({
        'id': book['id'],
        'title': book['title'],
        'author': book['author'],
        'year': book['year'],
        'isbn': book['isbn'],
        'created_at': book['created_at']
    }), 201


@app.route('/books', methods=['GET'])
def list_books():
    """List all books, with optional author filter."""
    author = request.args.get('author')
    db = get_db()
    cursor = db.cursor()
    
    if author:
        cursor.execute('SELECT * FROM books WHERE author LIKE ?', (f'%{author}%',))
    else:
        cursor.execute('SELECT * FROM books')
    
    books = cursor.fetchall()
    return jsonify([{
        'id': book['id'],
        'title': book['title'],
        'author': book['author'],
        'year': book['year'],
        'isbn': book['isbn'],
        'created_at': book['created_at']
    } for book in books]), 200


@app.route('/books/<int:book_id>', methods=['GET'])
def get_book(book_id):
    """Get a single book by ID."""
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM books WHERE id = ?', (book_id,))
    book = cursor.fetchone()
    
    if not book:
        return jsonify({'error': 'Book not found'}), 404
    
    return jsonify({
        'id': book['id'],
        'title': book['title'],
        'author': book['author'],
        'year': book['year'],
        'isbn': book['isbn'],
        'created_at': book['created_at']
    }), 200


@app.route('/books/<int:book_id>', methods=['PUT'])
def update_book(book_id):
    """Update a book."""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'Request body is required'}), 400
    
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM books WHERE id = ?', (book_id,))
    book = cursor.fetchone()
    
    if not book:
        return jsonify({'error': 'Book not found'}), 404
    
    # Build update query dynamically based on provided fields
    updates = []
    values = []
    
    if 'title' in data:
        errors = validate_book({'title': data['title']}, required_title=True, required_author=False)
        if errors:
            return jsonify({'error': errors}), 400
        updates.append('title = ?')
        values.append(data['title'].strip())
    
    if 'author' in data:
        errors = validate_book({'author': data['author']}, required_title=False, required_author=True)
        if errors:
            return jsonify({'error': errors}), 400
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
    
    # Fetch updated book
    cursor.execute('SELECT * FROM books WHERE id = ?', (book_id,))
    book = cursor.fetchone()
    
    return jsonify({
        'id': book['id'],
        'title': book['title'],
        'author': book['author'],
        'year': book['year'],
        'isbn': book['isbn'],
        'created_at': book['created_at']
    }), 200


@app.route('/books/<int:book_id>', methods=['DELETE'])
def delete_book(book_id):
    """Delete a book."""
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM books WHERE id = ?', (book_id,))
    book = cursor.fetchone()
    
    if not book:
        return jsonify({'error': 'Book not found'}), 404
    
    cursor.execute('DELETE FROM books WHERE id = ?', (book_id,))
    db.commit()
    
    return jsonify({'message': 'Book deleted successfully'}), 200


if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)
