import sqlite3
from flask import Flask, request, jsonify

app = Flask(__name__)

# Database setup
DATABASE = 'books.db'

def init_db():
    """Initialize the database with the books table"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER,
            isbn TEXT
        )
    """)
    conn.commit()
    conn.close()

def get_db_connection():
    """Create and return a database connection"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy}, 200

@app.route('/books', methods=['POST'])
def create_book():
    """Create a new book"""
    data = request.get_json()
    
    # Validate required fields
    if not data or 'title' not in data or not data['title'].strip():
        return jsonify({"error": "Title is required}, 400
    if not data or 'author' not in data or not data['author'].strip():
        return jsonify({"error": "Author is required}, 400
    )
    
    title = data['title'].strip()
    author = data['author'].strip()
    year = data.get('year')
    isbn = data.get('isbn')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
        (title, author, year, isbn)
    )
    book_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return jsonify({"id": book_id, "message": "Book created successfully}, 201

@app.route('/books', methods=['GET'])
def get_books():
    """Get all books with optional author filter"""
    author = request.args.get('author')
    conn = get_db_connection()
    
    if author:
        books = conn.execute(
            "SELECT * FROM books WHERE author LIKE ?", 
            (f"{author}",)
        ).fetchall()
    else:
        books = conn.execute("SELECT * FROM books").fetchall()
    
    conn.close()
    return jsonify([dict(book) for book in books]), 200

@app.route('/books/<int:book_id>', methods=['GET'])
def get_book(book_id):
    """Get a single book by ID"""
    conn = get_db_connection()
    book = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    conn.close()
    
    if book is None:
        return jsonify({"error": "Book not found}, 404
    )
    return jsonify(dict(book)), 200

@app.route('/books/<int:book_id>', methods=['PUT'])
def update_book(book_id):
    """Update a book by ID"""
    conn = get_db_connection()
    book = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    
    if book is None:
        conn.close()
        return jsonify({"error": "Book not found}, 404
    )
    
    # Validate required fields
    data = request.get_json()
    if not data or 'title' not in data or not data['title'].strip():
        return jsonify({"error": "Title is required}, 400
    if not data or 'author' not in data or not data['author'].strip():
        return jsonify({"error": "Author is required}, 400
    )
    
    title = data['title'].strip()
    author = data['author'].strip()
    year = data.get('year')
    isbn = data.get('isbn')
    
    conn.execute(
        "UPDATE books SET title=?, author=?, year=?, isbn=? WHERE id=?",
        (title, author, year, isbn, book_id)
    )
    conn.commit()
    conn.close()
    
    return jsonify({"message": "Book updated successfully}, 200
)

@app.route('/books/<int:book_id>', methods=['DELETE'])
def delete_book(book_id):
    """Delete a book by ID"""
    conn = get_db_connection()
    book = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    
    if book is None:
        conn.close()
        return jsonify({"error": "Book not found}, 404
    )
    conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
    conn.commit()
    conn.close()
    
    return jsonify({"message": "Book deleted successfully}, 200
)

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)