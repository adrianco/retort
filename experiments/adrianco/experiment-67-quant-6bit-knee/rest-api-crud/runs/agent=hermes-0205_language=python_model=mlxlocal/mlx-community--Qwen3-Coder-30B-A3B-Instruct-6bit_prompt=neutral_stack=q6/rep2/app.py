from flask import Flask, request, jsonify
import sqlite3
import os

app = Flask(__name__)

# Database file - make sure we use the DATABASE environment variable properly
DB_FILE = os.path.abspath(os.environ.get('DATABASE', 'books.db'))

def init_db():
    """Initialize the database with the books table if it doesn't exist."""
    print(f"Initializing database at: {DB_FILE}")
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    print("Creating books table...")
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
    print("Database initialized successfully")
    conn.close()

def get_db_connection():
    """Create and return a database connection."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
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
    
    # Validate that title and author are not empty
    if not title.strip() or not author.strip():
        return jsonify({'error': 'Title and author cannot be empty'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
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
    except Exception as e:
        conn.close()
        return jsonify({'error': 'Failed to create book'}), 500

@app.route('/books', methods=['GET'])
def get_books():
    """Get all books, optionally filtered by author."""
    author_filter = request.args.get('author')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if author_filter:
        cursor.execute('SELECT * FROM books WHERE author LIKE ?', (f'%{author_filter}%',))
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
    
    return jsonify(books_list), 200

@app.route('/books/<int:book_id>', methods=['GET'])
def get_book(book_id):
    """Get a single book by ID."""
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
    }), 200

@app.route('/books/<int:book_id>', methods=['PUT'])
def update_book(book_id):
    """Update a book."""
    data = request.get_json()
    
    # Validate required fields
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    # Check if book exists
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM books WHERE id = ?', (book_id,))
    book = cursor.fetchone()
    
    if book is None:
        conn.close()
        return jsonify({'error': 'Book not found'}), 404
    
    # Validate that title and author are not empty if provided
    title = data.get('title', book['title'])
    author = data.get('author', book['author'])
    
    if not title.strip() or not author.strip():
        conn.close()
        return jsonify({'error': 'Title and author cannot be empty'}), 400
    
    year = data.get('year', book['year'])
    isbn = data.get('isbn', book['isbn'])
    
    try:
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
    except Exception as e:
        conn.close()
        return jsonify({'error': 'Failed to update book'}), 500

@app.route('/books/<int:book_id>', methods=['DELETE'])
def delete_book(book_id):
    """Delete a book."""
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

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)