from flask import Flask, request, jsonify
import sqlite3
import os

app = Flask(__name__)

# Database file path
DB_FILE = 'books.db'

def init_db():
    """Initialize the database with the books table if it doesn't exist."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
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

def get_db_connection():
    """Create and return a database connection."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row  # This allows us to access columns by name
    return conn

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({'status': 'healthy'}), 200

@app.route('/books', methods=['POST'])
def create_book():
    """Create a new book."""
    data = request.get_json()
    
    # Validate required fields
    if not data or 'title' not in data or 'author' not in data:
        return jsonify({'error': 'Title and author are required'}), 400
    
    title = data['title']
    author = data['author']
    year = data.get('year')
    isbn = data.get('isbn')
    
    # Insert into database
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO books (title, author, year, isbn)
        VALUES (?, ?, ?, ?)
    ''', (title, author, year, isbn))
    conn.commit()
    book_id = cursor.lastrowid
    conn.close()
    
    # Return the created book with ID
    return jsonify({
        'id': book_id,
        'title': title,
        'author': author,
        'year': year,
        'isbn': isbn
    }), 201

@app.route('/books', methods=['GET'])
def get_books():
    """Get all books, optionally filtered by author."""
    author_filter = request.args.get('author')
    
    conn = get_db_connection()
    if author_filter:
        cursor = conn.execute('SELECT * FROM books WHERE author LIKE ?', (f'%{author_filter}%',))
    else:
        cursor = conn.execute('SELECT * FROM books')
    
    books = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify(books), 200

@app.route('/books/<int:book_id>', methods=['GET'])
def get_book(book_id):
    """Get a single book by ID."""
    conn = get_db_connection()
    cursor = conn.execute('SELECT * FROM books WHERE id = ?', (book_id,))
    book = cursor.fetchone()
    conn.close()
    
    if book is None:
        return jsonify({'error': 'Book not found'}), 404
    
    return jsonify(dict(book)), 200

@app.route('/books/<int:book_id>', methods=['PUT'])
def update_book(book_id):
    """Update a book."""
    data = request.get_json()
    
    # Validate required fields
    if not data or 'title' not in data or 'author' not in data:
        return jsonify({'error': 'Title and author are required'}), 400
    
    title = data['title']
    author = data['author']
    year = data.get('year')
    isbn = data.get('isbn')
    
    # Check if book exists
    conn = get_db_connection()
    cursor = conn.execute('SELECT * FROM books WHERE id = ?', (book_id,))
    book = cursor.fetchone()
    
    if book is None:
        conn.close()
        return jsonify({'error': 'Book not found'}), 404
    
    # Update the book
    cursor.execute('''
        UPDATE books 
        SET title = ?, author = ?, year = ?, isbn = ?
        WHERE id = ?
    ''', (title, author, year, isbn, book_id))
    conn.commit()
    conn.close()
    
    return jsonify({
        'id': book_id,
        'title': title,
        'author': author,
        'year': year,
        'isbn': isbn
    }), 200

@app.route('/books/<int:book_id>', methods=['DELETE'])
def delete_book(book_id):
    """Delete a book."""
    conn = get_db_connection()
    cursor = conn.execute('SELECT * FROM books WHERE id = ?', (book_id,))
    book = cursor.fetchone()
    
    if book is None:
        conn.close()
        return jsonify({'error': 'Book not found'}), 404
    
    cursor.execute('DELETE FROM books WHERE id = ?', (book_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'Book deleted successfully'}), 200

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)