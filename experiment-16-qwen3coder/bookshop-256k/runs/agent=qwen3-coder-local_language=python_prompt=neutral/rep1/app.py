import sqlite3
from flask import Flask, request, jsonify
from flask import g
import os

# Configuration
DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'books.db')
app = Flask(__name__)
from flask import Flask, request, jsonify
from flask import g
import os

# Configuration
DATABASE = 'books.db'
app = Flask(__name__)

# Initialize database
def init_db():
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

# Get database connection
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db

# Close database connection
@app.teardown_appcontext
def close_db(error):
    if 'db' in g:
        g.db.close()

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
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO books (title, author, year, isbn)
            VALUES (?, ?, ?, ?)
        ''', (title, author, year, isbn))
        conn.commit()
        
        book_id = cursor.lastrowid
        return jsonify({
            'id': book_id,
            'title': title,
            'author': author,
            'year': year,
            'isbn': isbn
        }), 201
        
    except sqlite3.IntegrityError:
        return jsonify({'error': 'ISBN must be unique'}), 400
    except Exception as e:
        return jsonify({'error': 'Failed to create book'}), 500

# GET /books - List all books with optional author filter
@app.route('/books', methods=['GET'])
def get_books():
    conn = get_db()
    cursor = conn.cursor()
    
    author = request.args.get('author')
    
    if author:
        cursor.execute('SELECT * FROM books WHERE author LIKE ?', (f'%{author}%',))
    else:
        cursor.execute('SELECT * FROM books')
    
    books = cursor.fetchall()
    
    return jsonify([{
        'id': book['id'],
        'title': book['title'],
        'author': book['author'],
        'year': book['year'],
        'isbn': book['isbn']
    } for book in books]), 200

# GET /books/{id} - Get a single book by ID
@app.route('/books/<int:book_id>', methods=['GET'])
def get_book(book_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM books WHERE id = ?', (book_id,))
    book = cursor.fetchone()
    
    if book is None:
        return jsonify({'error': 'Book not found'}), 404
    
    return jsonify({
        'id': book['id'],
        'title': book['title'],
        'author': book['author'],
        'year': book['year'],
        'isbn': book['isbn']
    }), 200

# PUT /books/{id} - Update a book
@app.route('/books/<int:book_id>', methods=['PUT'])
def update_book(book_id):
    conn = get_db()
    cursor = conn.cursor()
    
    # Check if book exists
    cursor.execute('SELECT * FROM books WHERE id = ?', (book_id,))
    existing_book = cursor.fetchone()
    
    if existing_book is None:
        return jsonify({'error': 'Book not found'}), 404
    
    data = request.get_json()
    
    # Validate required fields
    if not data or not data.get('title') or not data.get('author'):
        return jsonify({'error': 'Title and author are required'}), 400
    
    title = data['title']
    author = data['author']
    year = data.get('year')
    isbn = data.get('isbn')
    
    try:
        cursor.execute('''
            UPDATE books
            SET title = ?, author = ?, year = ?, isbn = ?
            WHERE id = ?
        ''', (title, author, year, isbn, book_id))
        conn.commit()
        
        return jsonify({
            'id': book_id,
            'title': title,
            'author': author,
            'year': year,
            'isbn': isbn
        }), 200
        
    except sqlite3.IntegrityError:
        return jsonify({'error': 'ISBN must be unique'}), 400
    except Exception as e:
        return jsonify({'error': 'Failed to update book'}), 500

# DELETE /books/{id} - Delete a book
@app.route('/books/<int:book_id>', methods=['DELETE'])
def delete_book(book_id):
    conn = get_db()
    cursor = conn.cursor()
    
    # Check if book exists
    cursor.execute('SELECT * FROM books WHERE id = ?', (book_id,))
    existing_book = cursor.fetchone()
    
    if existing_book is None:
        return jsonify({'error': 'Book not found'}), 404
    
    cursor.execute('DELETE FROM books WHERE id = ?', (book_id,))
    conn.commit()
    
    return jsonify({'message': 'Book deleted successfully'}), 200

# Initialize database on startup
init_db()

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5001)