from flask import Flask, request, jsonify
import sqlite3
import os

app = Flask(__name__)

# Database setup
def init_db():
    """Initialize the database with the books table"""
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
    """Get a database connection"""
    conn = sqlite3.connect('books.db')
    conn.row_factory = sqlite3.Row
    return conn

def clear_all_books():
    """Clear all books from the database for testing"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM books')
    conn.commit()
    conn.close()

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy'})

@app.route('/books', methods=['POST'])
def create_book():
    """Create a new book"""
    data = request.get_json()
    
    # Validate required fields
    if not data or not data.get('title') or not data.get('author'):
        return jsonify({'error': 'Title and author are required'}), 400
    
    # Extract book details
    title = data.get('title')
    author = data.get('author')
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
    
    # Get the created book
    book_id = cursor.lastrowid
    cursor.execute('SELECT * FROM books WHERE id = ?', (book_id,))
    book = cursor.fetchone()
    
    conn.close()
    
    # Return the created book
    return jsonify({
        'id': book['id'],
        'title': book['title'],
        'author': book['author'],
        'year': book['year'],
        'isbn': book['isbn']
    }), 201

@app.route('/books', methods=['GET'])
def get_books():
    """Get all books, optionally filtered by author"""
    author = request.args.get('author')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if author:
        cursor.execute('SELECT * FROM books WHERE author = ?', (author,))
    else:
        cursor.execute('SELECT * FROM books')
    
    books = cursor.fetchall()
    conn.close()
    
    # Convert to list of dictionaries
    books_list = []
    for book in books:
        books_list.append({
            'id': book['id'],
            'title': book['title'],
            'author': book['author'],
            'year': book['year'],
            'isbn': book['isbn']
        })
    
    return jsonify(books_list)

@app.route('/books/<int:book_id>', methods=['GET'])
def get_book(book_id):
    """Get a single book by ID"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM books WHERE id = ?', (book_id,))
    book = cursor.fetchone()
    conn.close()
    
    if book is None:
        return jsonify({'error': 'Book not found'}), 404
    
    return jsonify({
        'id': book['id'],
        'title': book['title'],
        'author': book['author'],
        'year': book['year'],
        'isbn': book['isbn']
    })

@app.route('/books/<int:book_id>', methods=['PUT'])
def update_book(book_id):
    """Update a book"""
    data = request.get_json()
    
    # Validate required fields
    if not data or not data.get('title') or not data.get('author'):
        return jsonify({'error': 'Title and author are required'}), 400
    
    # Check if book exists
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM books WHERE id = ?', (book_id,))
    book = cursor.fetchone()
    
    if book is None:
        conn.close()
        return jsonify({'error': 'Book not found'}), 404
    
    # Update the book
    title = data.get('title')
    author = data.get('author')
    year = data.get('year')
    isbn = data.get('isbn')
    
    cursor.execute('''
        UPDATE books 
        SET title = ?, author = ?, year = ?, isbn = ?
        WHERE id = ?
    ''', (title, author, year, isbn, book_id))
    conn.commit()
    
    # Get the updated book
    cursor.execute('SELECT * FROM books WHERE id = ?', (book_id,))
    updated_book = cursor.fetchone()
    conn.close()
    
    return jsonify({
        'id': updated_book['id'],
        'title': updated_book['title'],
        'author': updated_book['author'],
        'year': updated_book['year'],
        'isbn': updated_book['isbn']
    })

@app.route('/books/<int:book_id>', methods=['DELETE'])
def delete_book(book_id):
    """Delete a book"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM books WHERE id = ?', (book_id,))
    book = cursor.fetchone()
    
    if book is None:
        conn.close()
        return jsonify({'error': 'Book not found'}), 404
    
    cursor.execute('DELETE FROM books WHERE id = ?', (book_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'Book deleted successfully'}), 200

if __name__ == '__main__':
    # Initialize the database
    init_db()
    # Run the Flask app
    app.run(debug=True, host='0.0.0.0', port=5000)