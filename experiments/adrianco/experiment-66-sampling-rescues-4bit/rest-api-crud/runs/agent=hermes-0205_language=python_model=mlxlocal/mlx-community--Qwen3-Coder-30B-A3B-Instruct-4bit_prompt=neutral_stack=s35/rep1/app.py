import sqlite3
from flask import Flask, request, jsonify

app = Flask(__name__)

# Database setup
DATABASE = 'books.db'

def init_db():
    """Initialize the database with the books table"""
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    # Create books table if it doesn't exist
    c.execute('''
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER,
            isbn TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def get_db_connection():
    """Get a database connection"""
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    return conn

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy}), 200

@app.route('/books', methods=['POST'])
def create_book():
    """Create a new book"""
    data = request.get_json()
    
    # Validate required fields
    if not data or 'title' not in data or not data['title'].strip():
        return jsonify({"error": "Title is required}), 400
    if not data or 'author' not in data or not data['author'].strip():
        return jsonify({"error": "Author is required}), 400
    
    title = data['title'].strip()
    author = data['author'].strip()
    year = data.get('year')
    isbn = data.get('isbn')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
            (title, author, year, isbn)
        )
        conn.commit()
        book_id = cursor.lastrowid
        
        # Get the created book
        cursor.execute("SELECT * FROM books WHERE id = ?", (book_id,))
        book = cursor.fetchone()
        
        return jsonify({
 "id": book[0],
 "title": book[1],
 "author": book[2],
 "year": book[3],
 "isbn": book[4],
 "created_at": book[5],
 "updated_at": book[6]
        }), 201
    except sqlite3.Error as e:
        conn.rollback()
        return jsonify({"error": "Database error}), 500
    finally:
        conn.close()

@app.route('/books', methods=['GET'])
def get_books():
    """List all books with optional author filter"""
    author = request.args.get('author', '')
    if author:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM books WHERE author LIKE ?", (f"%{author}",))
        books = cursor.fetchall()
        conn.close()
        return jsonify([dict(book) for book in books]), 200
    else:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM books")
        books = cursor.fetchall()
        conn.close()
        return jsonify([dict(book) for book in books]), 200

@app.route('/books/<int:book_id>', methods=['GET'])
def get_book(book_id):
    """Get a single book by ID"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM books WHERE id = ?", (book_id,))
    book = cursor.fetchone()
    
    if book is None:
        conn.close()
        return jsonify({"error": "Book not found}), 404
    else:
        conn.close()
        return jsonify(dict(book)), 200

@app.route('/books/<int:book_id>', methods=['PUT'])
def update_book(book_id):
    """Update a book"""
    data = request.get_json()
    
 # Validate required fields
    if not data or 'title' not in data or not data['title'].strip():
        return jsonify({"error": "Title is required}), 400
    if not data or 'author' not in data or not data['author'].strip():
        return jsonify({"error": "Author is required}), 400
    
    title = data['title'].strip()
    author = data['author'].strip()
    year = data.get('year')
    isbn = data.get('isbn')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if book exists
    cursor.execute("SELECT * FROM books WHERE id = ?", (book_id,))
    book = cursor.fetchone()
    
    if not book:
        conn.close()
        return jsonify({"error": "Book not found}), 404
    else:
        try:
            cursor.execute(
                "UPDATE books SET title=?, author=?, year=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                (title, author, year, book_id)
            )
            conn.commit()
            cursor.execute("SELECT * FROM books WHERE id = ?", (book_id,))
            updated_book = cursor.fetchone()
            
            return jsonify({
 "id": updated_book[0],
 "title": updated_book[1],
 "author": updated_book[2],
 "year": updated_book[3],
 "isbn": updated_book[4],
 "created_at": updated_book[5],
 "updated_at": updated_book[6]
            }), 200
        except sqlite3.Error as e:
            conn.rollback()
            return jsonify({"error": "Database error}), 500
        finally:
            conn.close()

@app.route('/books/<int:book_id>', methods=['DELETE'])
def delete_book(book_id):
    """Delete a book"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if book exists
    cursor.execute("SELECT * FROM books WHERE id = ?", (book_id,))
    book = cursor.fetchone()
    
    if not book:
        conn.close()
        return jsonify({"error": "Book not found}), 404
    else:
        cursor.execute("DELETE FROM books WHERE id = ?", (book_id,))
        conn.commit()
        conn.close()
        return jsonify({"message": "Book deleted successfully}), 200