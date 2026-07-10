import sqlite3
import os
from flask import Flask, request, jsonify
from typing import Dict, List, Optional

# Initialize Flask app
app = Flask(__name__)

# Database setup
DB_NAME = "books.db"

def init_db():
    """Initialize the SQLite database with books table"""
    conn = sqlite3.connect(DB_NAME)
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
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row  # This allows us to access columns by name
    return conn

def validate_book_data(data: Dict) -> List[str]:
    """Validate book data"""
    errors = []
    
    if not data.get('title'):
        errors.append("Title is required")
    
    if not data.get('author'):
        errors.append("Author is required")
    
    return errors

# Health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy"}), 200

# POST /books - Create a new book
@app.route('/books', methods=['POST'])
def create_book():
    """Create a new book"""
    data = request.get_json()
    
    # Validate input
    errors = validate_book_data(data)
    if errors:
        return jsonify({"errors": errors}), 400
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO books (title, author, year, isbn)
            VALUES (?, ?, ?, ?)
        ''', (data['title'], data['author'], data.get('year'), data.get('isbn')))
        
        book_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # Return the created book
        return jsonify({
            "id": book_id,
            "title": data['title'],
            "author": data['author'],
            "year": data.get('year'),
            "isbn": data.get('isbn')
        }), 201
        
    except sqlite3.IntegrityError as e:
        if "UNIQUE constraint failed" in str(e):
            return jsonify({"error": "ISBN must be unique"}), 400
        else:
            return jsonify({"error": "Database error"}), 500
    except Exception as e:
        return jsonify({"error": "Internal server error"}), 500

# GET /books - List all books with optional author filter
@app.route('/books', methods=['GET'])
def get_books():
    """Get all books, optionally filtered by author"""
    author = request.args.get('author')
    
    try:
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
                "id": book['id'],
                "title": book['title'],
                "author": book['author'],
                "year": book['year'],
                "isbn": book['isbn']
            })
        
        return jsonify(books_list), 200
        
    except Exception as e:
        return jsonify({"error": "Internal server error"}), 500

# GET /books/{id} - Get a single book by ID
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
            return jsonify({"error": "Book not found"}), 404
        
        return jsonify({
            "id": book['id'],
            "title": book['title'],
            "author": book['author'],
            "year": book['year'],
            "isbn": book['isbn']
        }), 200
        
    except Exception as e:
        return jsonify({"error": "Internal server error"}), 500

# PUT /books/{id} - Update a book
@app.route('/books/<int:book_id>', methods=['PUT'])
def update_book(book_id):
    """Update a book"""
    data = request.get_json()
    
    # Validate input
    errors = validate_book_data(data)
    if errors:
        return jsonify({"errors": errors}), 400
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if book exists
        cursor.execute('SELECT * FROM books WHERE id = ?', (book_id,))
        existing_book = cursor.fetchone()
        
        if existing_book is None:
            conn.close()
            return jsonify({"error": "Book not found"}), 404
        
        # Update the book
        cursor.execute('''
            UPDATE books 
            SET title = ?, author = ?, year = ?, isbn = ?
            WHERE id = ?
        ''', (data['title'], data['author'], data.get('year'), data.get('isbn'), book_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            "id": book_id,
            "title": data['title'],
            "author": data['author'],
            "year": data.get('year'),
            "isbn": data.get('isbn')
        }), 200
        
    except sqlite3.IntegrityError as e:
        if "UNIQUE constraint failed" in str(e):
            return jsonify({"error": "ISBN must be unique"}), 400
        else:
            return jsonify({"error": "Database error"}), 500
    except Exception as e:
        return jsonify({"error": "Internal server error"}), 500

# DELETE /books/{id} - Delete a book
@app.route('/books/<int:book_id>', methods=['DELETE'])
def delete_book(book_id):
    """Delete a book"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if book exists
        cursor.execute('SELECT * FROM books WHERE id = ?', (book_id,))
        existing_book = cursor.fetchone()
        
        if existing_book is None:
            conn.close()
            return jsonify({"error": "Book not found"}), 404
        
        # Delete the book
        cursor.execute('DELETE FROM books WHERE id = ?', (book_id,))
        conn.commit()
        conn.close()
        
        return jsonify({"message": "Book deleted successfully"}), 200
        
    except Exception as e:
        return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5001)