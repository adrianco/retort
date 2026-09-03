from flask import Flask, request, jsonify
import sqlite3
import os

app = Flask(__name__)

# Database setup
def init_db():
    """Initialize the SQLite database with books table"""
    conn = sqlite3.connect('books.db')
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

# Helper function to get database connection
def get_db_connection():
    conn = sqlite3.connect('books.db')
    conn.row_factory = sqlite3.Row
    return conn

# Health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy'}), 200

# Create a new book
@app.route('/books', methods=['POST'])
def create_book():
    data = request.get_json()
    
    # Validate required fields
    if not data or 'title' not in data or 'author' not in data:
        return jsonify({'error': 'Title and author are required'}), 400
    
    title = data['title']
    author = data['author']
    year = data.get('year')
    isbn = data.get('isbn')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            'INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)',
            (title, author, year, isbn)
        )
        conn.commit()
        book_id = cursor.lastrowid
        
        # Retrieve the created book
        cursor.execute('SELECT * FROM books WHERE id = ?', (book_id,))
        book = cursor.fetchone()
        
        conn.close()
        return jsonify(dict(book)), 201
    except Exception as e:
        conn.close()
        return jsonify({'error': 'Failed to create book'}), 500

# Get all books with optional author filter
@app.route('/books', methods=['GET'])
def get_books():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    author = request.args.get('author')
    
    if author:
        cursor.execute('SELECT * FROM books WHERE author = ?', (author,))
    else:
        cursor.execute('SELECT * FROM books')
    
    books = cursor.fetchall()
    conn.close()
    
    return jsonify([dict(book) for book in books]), 200

# Get a single book by ID
@app.route('/books/<int:book_id>', methods=['GET'])
def get_book(book_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM books WHERE id = ?', (book_id,))
    book = cursor.fetchone()
    
    conn.close()
    
    if book is None:
        return jsonify({'error': 'Book not found'}), 404
    
    return jsonify(dict(book)), 200

# Update a book
@app.route('/books/<int:book_id>', methods=['PUT'])
def update_book(book_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if book exists
    cursor.execute('SELECT * FROM books WHERE id = ?', (book_id,))
    book = cursor.fetchone()
    
    if book is None:
        conn.close()
        return jsonify({'error': 'Book not found'}), 404
    
    data = request.get_json()
    
    # Validate required fields (title and author)
    if not data or 'title' not in data or 'author' not in data:
        conn.close()
        return jsonify({'error': 'Title and author are required'}), 400
    
    title = data['title']
    author = data['author']
    year = data.get('year')
    isbn = data.get('isbn')
    
    try:
        cursor.execute(
            'UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?',
            (title, author, year, isbn, book_id)
        )
        conn.commit()
        
        # Retrieve the updated book
        cursor.execute('SELECT * FROM books WHERE id = ?', (book_id,))
        updated_book = cursor.fetchone()
        
        conn.close()
        return jsonify(dict(updated_book)), 200
    except Exception as e:
        conn.close()
        return jsonify({'error': 'Failed to update book'}), 500

# Delete a book
@app.route('/books/<int:book_id>', methods=['DELETE'])
def delete_book(book_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if book exists
    cursor.execute('SELECT * FROM books WHERE id = ?', (book_id,))
    book = cursor.fetchone()
    
    if book is None:
        conn.close()
        return jsonify({'error': 'Book not found'}), 404
    
    try:
        cursor.execute('DELETE FROM books WHERE id = ?', (book_id,))
        conn.commit()
        conn.close()
        return jsonify({'message': 'Book deleted successfully'}), 200
    except Exception as e:
        conn.close()
        return jsonify({'error': 'Failed to delete book'}), 500

# Initialize database on startup
if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)