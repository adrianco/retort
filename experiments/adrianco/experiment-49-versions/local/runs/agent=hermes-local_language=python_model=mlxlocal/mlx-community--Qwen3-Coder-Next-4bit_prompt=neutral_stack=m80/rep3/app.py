"""Book Collection REST API Service."""

import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify, g

app = Flask(__name__)
DATABASE = 'books.db'


def get_db():
    """Get database connection for current request context."""
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(error):
    """Close database connection at end of request."""
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    """Initialize the database with required schema."""
    db = sqlite3.connect(DATABASE)
    cursor = db.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER,
            isbn TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT
        )
    ''')
    db.commit()
    db.close()


def validate_book_data(data, require_title=True, require_author=True):
    """Validate book data and return error message if invalid."""
    if require_title and ('title' not in data or not data['title'] or not str(data['title']).strip()):
        return 'Title is required'
    if require_author and ('author' not in data or not data['author'] or not str(data['author']).strip()):
        return 'Author is required'
    if 'year' in data and data['year'] is not None:
        try:
            year = int(data['year'])
            if year < 0 or year > 9999:
                return 'Year must be a valid year (0-9999)'
        except (ValueError, TypeError):
            return 'Year must be a valid integer'
    return None


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({'status': 'healthy'}), 200


@app.route('/books', methods=['GET'])
def list_books():
    """List all books, optionally filtered by author."""
    db = get_db()
    cursor = db.cursor()
    
    author = request.args.get('author')
    
    if author:
        cursor.execute('SELECT * FROM books WHERE author = ?', (author,))
    else:
        cursor.execute('SELECT * FROM books')
    
    books = cursor.fetchall()
    result = []
    for book in books:
        result.append({
            'id': book['id'],
            'title': book['title'],
            'author': book['author'],
            'year': book['year'],
            'isbn': book['isbn'],
            'created_at': book['created_at'],
            'updated_at': book['updated_at']
        })
    
    return jsonify(result), 200


@app.route('/books', methods=['POST'])
def create_book():
    """Create a new book."""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'Request body is required'}), 400
    
    # Validate required fields
    error = validate_book_data(data, require_title=True, require_author=True)
    if error:
        return jsonify({'error': error}), 400
    
    db = get_db()
    cursor = db.cursor()
    
    now = datetime.utcnow().isoformat()
    cursor.execute('''
        INSERT INTO books (title, author, year, isbn, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        str(data['title']).strip(),
        str(data['author']).strip(),
        data.get('year'),
        data.get('isbn'),
        now,
        now
    ))
    db.commit()
    
    book_id = cursor.lastrowid
    cursor.execute('SELECT * FROM books WHERE id = ?', (book_id,))
    book = cursor.fetchone()
    
    result = {
        'id': book['id'],
        'title': book['title'],
        'author': book['author'],
        'year': book['year'],
        'isbn': book['isbn'],
        'created_at': book['created_at'],
        'updated_at': book['updated_at']
    }
    
    return jsonify(result), 201


@app.route('/books/<int:book_id>', methods=['GET'])
def get_book(book_id):
    """Get a single book by ID."""
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute('SELECT * FROM books WHERE id = ?', (book_id,))
    book = cursor.fetchone()
    
    if not book:
        return jsonify({'error': 'Book not found'}), 404
    
    result = {
        'id': book['id'],
        'title': book['title'],
        'author': book['author'],
        'year': book['year'],
        'isbn': book['isbn'],
        'created_at': book['created_at'],
        'updated_at': book['updated_at']
    }
    
    return jsonify(result), 200


@app.route('/books/<int:book_id>', methods=['PUT'])
def update_book(book_id):
    """Update a book."""
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute('SELECT * FROM books WHERE id = ?', (book_id,))
    existing_book = cursor.fetchone()
    
    if not existing_book:
        return jsonify({'error': 'Book not found'}), 404
    
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'Request body is required'}), 400
    
    # Validate required fields (title and author still required for update)
    error = validate_book_data(data, require_title=True, require_author=True)
    if error:
        return jsonify({'error': error}), 400
    
    now = datetime.utcnow().isoformat()
    cursor.execute('''
        UPDATE books 
        SET title = ?, author = ?, year = ?, isbn = ?, updated_at = ?
        WHERE id = ?
    ''', (
        str(data['title']).strip(),
        str(data['author']).strip(),
        data.get('year'),
        data.get('isbn'),
        now,
        book_id
    ))
    db.commit()
    
    cursor.execute('SELECT * FROM books WHERE id = ?', (book_id,))
    book = cursor.fetchone()
    
    result = {
        'id': book['id'],
        'title': book['title'],
        'author': book['author'],
        'year': book['year'],
        'isbn': book['isbn'],
        'created_at': book['created_at'],
        'updated_at': book['updated_at']
    }
    
    return jsonify(result), 200


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
