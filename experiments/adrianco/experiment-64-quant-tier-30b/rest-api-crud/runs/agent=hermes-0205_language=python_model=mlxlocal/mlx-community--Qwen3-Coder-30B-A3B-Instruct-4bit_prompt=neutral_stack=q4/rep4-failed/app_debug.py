import sqlite3
from flask import Flask, request, jsonify, abort
import os
from datetime import datetime

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
            isbn TEXT UNIQUE
        )
    ''')
    conn.commit()
    conn.close()

def get_db_connection():
    """Get database connection"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})

@app.route('/books', methods=['POST'])
def create_book():
    """Create a new book"""
    data = request.get_json()
    
    # Validate required fields
    if not data or 'title' not in data or not data['title'].strip():
        abort(400, description="Title is required")
    
    if not data or 'author' not in data or not not data['author'].strip():
        abort(400, description="Author is required")
    
    # Validate year if provided
    if 'year' in data:
        try:
            year = int(data['year'])
            if year < 1000 or year > datetime.now().year + 1:
                abort(400, description="Year must be a valid year")
        except ValueError:
            abort(400, description="Year must be a valid number")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (data['title'], data['author'], data.get('year'), data.get('isbn'))
        )
        book_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({
            "id": book_id,
            "title": data['title'],
            "author": data['author'],
            "year": data.get('year'),
            "isbn": data.get('isbn')
        }), 201
    except sqlite3.IntegrityError as e:
        conn.close()
        abort(400, description="ISBN must be unique")

@app.route('/books', methods=['GET'])
def list_books():
    """List all books with optional filtering"""
    author = request.args.get('author')
    
    conn = get_db_connection()
    if author:
        query = "SELECT * FROM books WHERE author = ?"
        books = conn.execute(query, (author,)).fetchall()
    else:
        query = "SELECT * FROM books"
        books = conn.execute(query).fetchall()
    
    conn.close()
    return jsonify([dict(book) for book in books]), 200

@app.route('/books/<int:book_id>', methods=['GET'])
def get_book(book_id):
    """Get a single book by ID"""
    conn = get_db_connection()
    book = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    conn.close()
    
    if book is None:
        abort(404, description="Book not found")
    
    return jsonify(dict(book)), 200

@app.route('/books/<int:book_id>', methods=['PUT'])
def update_book(book_id):
    """Update a book by ID"""
    data = request.get_json()
    
    # Validate required fields
    if not data or 'title' not in data or not data['title'].strip():
        abort(400, description="Title is required")
    
    if not data or 'author' not in data or not data['author'].strip():
        abort(400, description="Author is required")
    
    # Validate year if provided
    if 'year' in data:
        try:

            year = int(data['year'])
            if year < 1000 or year > datetime.now().year + 1:
                abort(400, description="Year must be a valid year")
        except ValueError:
            abort(400, description="Year must be a valid number")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if book exists
    existing_book = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    if existing_book is None:
        abort(404, description="Book not found")
    
    # Update the book
    cursor.execute(
        "UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?", 
        (data['title'], data['author'], data.get('year'), data.get('isbn'), book_id)
    )
    
    conn.commit()
    conn.close()
    
    return jsonify({
        "id": book_id,
 "title": data['title'],
 "author": data['author'],
 "year": data.get('year'),
 "isbn": data.get('isbn')
    }), 200

@app.route('/books/<int:book_id>', methods=['DELETE'])
def delete_book(book_id):
    """Delete a book by ID"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if book exists
    existing_book = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    if existing_book is None:
        abort(404, description="Book not found")
    
    cursor.execute("DELETE FROM books WHERE id = ?", (book_id,))
    conn.commit()
    conn.close()
    
    return jsonify({"message": "Book deleted successfully"}, 200)

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({"error": str(error)}, 404)

@app.errorhandler(400)
def bad_request(error):
    """Handle 400 errors"""
    return jsonify({"error": str(error)}, 400)

if __name__ == '__main__':
    init_db()
    app.run(debug=True)