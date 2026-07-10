import sqlite3
import os
from flask import Flask, request, jsonify
from werkzeug.exceptions import NotFound, BadRequest

# Initialize Flask app
app = Flask(__name__)

# Database setup
DATABASE = 'books.db'

def init_db():
    """Initialize the database with the books table"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER,
            isbn TEXT UNIQUE
        )
    ''')
    conn.commit()
    conn.close()

def get_db_connection():
    """Get a database connection"""
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
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO books (title, author, year, isbn)
            VALUES (?, ?, ?, ?)
        ''', (title, author, year, isbn))
        conn.commit()
        book_id = cursor.lastrowid
        conn.close()
        
        # Return the created book
        return jsonify({
            'id': book_id,
            'title': title,
            'author': author,
            'year': year,
            'isbn': isbn
        }), 201
        
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({'error': 'ISBN already exists'}), 400
    except Exception as e:
        conn.close()
        return jsonify({'error': 'Failed to create book'}), 500

@app.route('/books', methods=['GET'])
def get_books():
    """Get all books with optional author filter"""
    author = request.args.get('author')
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if author:
            cursor.execute('''
                SELECT * FROM books WHERE author = ?
            ''', (author,))
        else:
            cursor.execute('SELECT * FROM books')
            
        books = cursor.fetchall()
        conn.close()
        
        # Convert to list of dictionaries
        books_list = [dict(book) for book in books]
        return jsonify(books_list), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to fetch books'}), 500

@app.route('/books/<int:book_id>', methods=['GET'])
def get_book(book_id):
    """Get a single book by ID"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM books WHERE id = ?', (book_id,))
        book = cursor.fetchone()
        conn.close()
        
        if book is None:
            return jsonify({'error': 'Book not found'}), 404
            
        return jsonify(dict(book)), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to fetch book'}), 500

@app.route('/books/<int:book_id>', methods=['PUT'])
def update_book(book_id):
    """Update a book"""
    data = request.get_json()
    
    # Validate that title and author are provided
    if not data or 'title' not in data or 'author' not in data:
        return jsonify({'error': 'Title and author are required'}), 400
    
    title = data['title']
    author = data['author']
    year = data.get('year')
    isbn = data.get('isbn')
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE books 
            SET title = ?, author = ?, year = ?, isbn = ?
            WHERE id = ?
        ''', (title, author, year, isbn, book_id))
        
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({'error': 'Book not found'}), 404
            
        conn.commit()
        conn.close()
        
        # Return the updated book
        return jsonify({
            'id': book_id,
            'title': title,
            'author': author,
            'year': year,
            'isbn': isbn
        }), 200
        
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({'error': 'ISBN already exists'}), 400
    except Exception as e:
        conn.close()
        return jsonify({'error': 'Failed to update book'}), 500

@app.route('/books/<int:book_id>', methods=['DELETE'])
def delete_book(book_id):
    """Delete a book"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM books WHERE id = ?', (book_id,))
        
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({'error': 'Book not found'}), 404
            
        conn.commit()
        conn.close()
        
        return jsonify({'message': 'Book deleted successfully'}), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to delete book'}), 500

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)