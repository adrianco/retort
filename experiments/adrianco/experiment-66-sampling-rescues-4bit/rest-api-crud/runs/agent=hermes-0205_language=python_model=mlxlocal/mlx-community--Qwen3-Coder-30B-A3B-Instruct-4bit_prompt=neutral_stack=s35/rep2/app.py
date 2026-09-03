#!/usr/bin/env python3
import sqlite3
from flask import Flask, request, jsonify

app = Flask(__name__)

# Initialize database
def init_db():
    conn = sqlite3.connect('books.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS books
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  title TEXT NOT NULL,
                  author TEXT NOT NULL,
                  year INTEGER,
                  isbn TEXT)''')
    conn.commit()
    conn.close()

# Health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy})

# Create a new book
@app.route('/books', methods=['POST'])
def create_book():
    data = request.get_json()
    
    # Validate required fields
    if not data or 'title' not in data or not data['title'].strip():
        return jsonify({"error": "Title is required}), 400
    if not data or 'author' not in data or not data['author'].strip():
        return jsonify({"error": "Author is required}, 400
    
    title = data['title'].strip()
    author = data['author'].strip()
    year = data.get('year')
    isbn = data.get('isbn')
    
    conn = sqlite3.connect('books.db')
    c = conn.cursor()
    c.execute("INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)",
              (title, author, year, isbn))
    conn.commit()
    book_id = c.lastrowid
    conn.close()
    
    return jsonify({"id": book_id, "message": "Book created successfully}), 201

# Get all books with optional filtering
@app.route('/books', methods=['GET'])
def get_books():
    conn = sqlite3.connect('books.db')
    c = conn.cursor()
    
    # Handle query parameters
    author = request.args.get('author')
    if author:
        c.execute("SELECT * FROM books WHERE author LIKE ?", (f"%{author}%",))
    else:
        c.execute("SELECT * FROM books")
    
    books = c.fetchall()
    conn.close()
    
    books_list = []
    for book in books:
        book_dict = {
            "id": book[0],
            "title": book[1],
            "author": book[2],
            "year": book[3],
            "isbn": book[4]
        }
        books_list.append(book_dict)
    
    return jsonify(books_list), 200

# Get a single book by ID
@app.route('/books/<int:book_id>', methods=['GET'])
def get_book(book_id):
    conn = sqlite3.connect('books.db')
    c = conn.cursor()
    c.execute("SELECT * FROM books WHERE id = ?", (book_id,))
    book = c.fetchone()
    conn.close()
    
    if book is None:
        return jsonify({"error": "Book not found}, 404
    else:
        book_dict = {
            "id": book[0],
            "title": book[1],
            "author": book[2],
            "year": book[3],
            "isbn": book[4]
        }
        return jsonify(book_dict), 200

# Update a book
@app.route('/books/<int:book_id>', methods=['PUT'])
def update_book(book_id):
    conn = sqlite3.connect('books.db')
    c = conn.cursor()
    
    # Check if book exists
    c.execute("SELECT * FROM books WHERE id = ?", (book_id,))
    existing_book = c.fetchone()
    
    if not existing_book:
        return jsonify({"error": "Book not found}, 404
    
    data = request.get_json()
    
    # Validate required fields if provided
    title = data.get('title')
    author = data.get('author')
    year = data.get('year')
    isbn = data.get('isbn')
    
    # If title or author are provided, validate them
    if 'title' in data and not data['title'].strip():
        return jsonify({"error": "Title cannot be empty}, 400
    if 'author' in data and not data['author'].strip():
        return jsonify({"error": "Author cannot be empty}, 400
    
    # Prepare update query
    update_fields = []
    update_values = []
    
    if title is not None:
        update_fields.append("title = ?")
        update_values.append(title.strip() if isinstance(title, str) else title)
    if author is not None:
        update_fields.append("author = ?")
        update_values.append(author.strip() if isinstance(author, str) else author)
    if year is not None:
        update_fields.append("year = ?")
        update_values.append(year)
    if isbn is not None:
        update_fields.append("isbn = ?")
        update_values.append(isbn)
    
    if not update_fields:
        return jsonify({"error": "No valid fields provided for update}, 400
    
    # Build and execute the update query
    query = f"UPDATE books SET {', '.join(update_fields)} WHERE id = ?"
    update_values.append(book_id)
    
    c.execute(query, update_values)
    conn.commit()
    
    if c.rowcount == 0:
        return jsonify({"error": "Book not found}, 404
    else:
        return jsonify({"message": "Book updated successfully}, 200

# Delete a book
@app.route('/books/<int:book_id>', methods=['DELETE'])
def delete_book(book_id):
    conn = sqlite3.connect('books.db')
    c = conn.cursor()
    
    # Check if book exists
    c.execute("SELECT * FROM books WHERE id = ?", (book_id,))
    existing_book = c.fetchone()
    
    if not existing_book:
        return jsonify({"error": "Book not found}, 404
    
    c.execute("DELETE FROM books WHERE id = ?", (book_id,))
    conn.commit()
    conn.close()
    
    return jsonify({"message": "Book deleted successfully}, 200

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='127.0.0.1', port=5000)