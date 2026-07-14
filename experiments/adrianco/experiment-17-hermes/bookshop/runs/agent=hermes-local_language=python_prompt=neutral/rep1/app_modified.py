from flask import Flask, request, jsonify
import sqlite3
import os

app = Flask(__name__)

# Database initialization
def init_db():
    conn = sqlite3.connect('books.db')
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

# Helper function to get database connection
def get_db_connection():
    conn = sqlite3.connect('books.db')
    conn.row_factory = sqlite3.Row
    return conn

# Health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy'}), 200

# POST /books - Create a new book
@app.route('/books', methods=['POST'])
def create_book():
    data = request.get_json()
    
    # Validate required fields
    if not data or not data.get('title') or not data.get('author'):
        return jsonify({'error': 'Title and author are required'}), 400
    
    title = data['title']
    author = data['author']
    year = data.get('year')
    isbn = data.get('isbn')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO books (title, author, year, isbn)
        VALUES (?, ?, ?, ?)
    ''', (title, author, year, isbn))
    conn.commit()
    
    book_id = cursor.lastrowid
    conn.close()
    
    return jsonify({
        'id': book_id,
        'title': title,
        'author': author,
        'year': year,
        'isbn': isbn
    }), 201

# GET /books - List all books with optional author filter
@app.route('/books', methods=['GET'])
def get_books():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    author = request.args.get('author')
    
    if author:
        cursor.execute('SELECT * FROM books WHERE author LIKE ?', (f'%{author}%',))
    else:
        cursor.execute('SELECT * FROM books')
    
    books = cursor.fetchall()
    conn.close()
    
    return jsonify([dict(book) for book in books]), 200

# GET /books/{id} - Get a single book by ID
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

# PUT /books/{id} - Update a book
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
    
    # Validate required fields
    if not data or not data.get('title') or not data.get('author'):
        conn.close()
        return jsonify({'error': 'Title and author are required'}), 400
    
    title = data['title']
    author = data['author']
    year = data.get('year')
    isbn = data.get('isbn')
    
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

# DELETE /books/{id} - Delete a book
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
    
    cursor.execute('DELETE FROM books WHERE id = ?', (book_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'Book deleted successfully'}), 200

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5001)
