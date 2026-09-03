from flask import Flask, request, jsonify
import sqlite3
import os

app = Flask(__name__)

# Database setup
DATABASE = 'books.db'

def init_db():
    """Initialize the database with the books table"""
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('''
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
    """Create a database connection"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy'}), 200

@app.route('/books', methods=['POST'])
def create_book():
    """Create a new book"""
    data = request.get_json()
    
    # Validate required fields
    if not data or 'title' not in data or 'author' not in data:
        return jsonify({'error': 'Title and author are required'}), 400
    
    title = data['title']
    author = data['author']
    year = data.get('year')
    isbn = data.get('isbn')
    
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            'INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)',
            (title, author, year, isbn)
        )
        conn.commit()
        book_id = cursor.lastrowid
        conn.close()
        
        # Return the created book
        conn = get_db_connection()
        book = conn.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()
        conn.close()
        
        return jsonify(dict(book)), 201
    except Exception as e:
        conn.close()
        return jsonify({'error': 'Failed to create book'}), 500

@app.route('/books', methods=['GET'])
def get_books():
    """Get all books, optionally filtered by author"""
    author = request.args.get('author')
    
    conn = get_db_connection()
    if author:
        books = conn.execute('SELECT * FROM books WHERE author LIKE ?', (f'%{author}%',)).fetchall()
    else:
        books = conn.execute('SELECT * FROM books').fetchall()
    conn.close()
    
    return jsonify([dict(book) for book in books])

@app.route('/books/<int:book_id>', methods=['GET'])
def get_book(book_id):
    """Get a single book by ID"""
    conn = get_db_connection()
    book = conn.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()
    conn.close()
    
    if book is None:
        return jsonify({'error': 'Book not found'}), 404
    
    return jsonify(dict(book))

@app.route('/books/<int:book_id>', methods=['PUT'])
def update_book(book_id):
    """Update a book"""
    data = request.get_json()
    
    # Validate required fields
    if not data or 'title' not in data or 'author' not in data:
        return jsonify({'error': 'Title and author are required'}), 400
    
    title = data['title']
    author = data['author']
    year = data.get('year')
    isbn = data.get('isbn')
    
    conn = get_db_connection()
    book = conn.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()
    
    if book is None:
        conn.close()
        return jsonify({'error': 'Book not found'}), 404
    
    try:
        conn.execute(
            'UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?',
            (title, author, year, isbn, book_id)
        )
        conn.commit()
        conn.close()
        
        # Return the updated book
        conn = get_db_connection()
        updated_book = conn.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()
        conn.close()
        
        return jsonify(dict(updated_book))
    except Exception as e:
        conn.close()
        return jsonify({'error': 'Failed to update book'}), 500

@app.route('/books/<int:book_id>', methods=['DELETE'])
def delete_book(book_id):
    """Delete a book"""
    conn = get_db_connection()
    book = conn.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()
    
    if book is None:
        conn.close()
        return jsonify({'error': 'Book not found'}), 404
    
    try:
        conn.execute('DELETE FROM books WHERE id = ?', (book_id,))
        conn.commit()
        conn.close()
        return jsonify({'message': 'Book deleted successfully'}), 200
    except Exception as e:
        conn.close()
        return jsonify({'error': 'Failed to delete book'}), 500

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5001)