#!/usr/bin/env python3
import sqlite3
from flask import Flask, request, jsonify, abort

app = Flask(__name__)

# Database setup
def init_db():
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

def get_db_connection():
    conn = sqlite3.connect('books.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy}), 200

@app.route('/books', methods=['POST'])
def create_book():
    data = request.get_json()
    
    # Validate required fields
    if not data or 'title' not in data or not data['title'].strip():
        return jsonify({"error": "Title is required}, 400
    if not data or 'author' not in data or not data['author'].strip():
        return jsonify({"error": "Author is required}, 400
    
    # Validate year if provided
    if 'year' in data and data['year'] is not None:
        try:
            year = int(data['year'])
        except ValueError:
            return jsonify({"error": "Year must be a valid integer}, 400
        if year < 0 or year > 2024:
            return jsonify({"error": "Year must be a valid year}, 400

    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO books (title, author, year, isbn) 
        VALUES (?, ?, ?, ?)
    ''', (data['title'], data['author'], data.get('year'), data.get('isbn')))
    
    book_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return jsonify({"id": book_id}), 201

@app.route('/books', methods=['GET'])
def get_books():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Handle query parameters
    author = request.args.get('author')
    if author:
        cursor.execute('SELECT * FROM books WHERE author = ?', (author,))
        books = cursor.fetchall()
    else:
        cursor.execute('SELECT * FROM books')
        books = cursor.fetchall()
    
    conn.close()
    return jsonify([dict(book) for book in books]), 200

@app.route('/books/<int:book_id>', methods=['GET'])
def get_book(book_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM books WHERE id = ?', (book_id,))
    book = cursor.fetchone()
    
    if book is None:
        abort(404)
    
    conn.close()
    return jsonify(dict(book)), 200

@app.route('/books/<int:book_id>', methods=['PUT'])
def update_book(book_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if book exists
    cursor.execute('SELECT * FROM books WHERE id = ?', (book_id,))
    book = cursor.fetchone()
    
    if book is None:
        abort(404)
    
    data = request.get_json()
    
    # Validate required fields
    if not data or 'title' not in data or not data['title'].strip():
        return jsonify({"error": "Title is required}, 400
    if not data or 'author' not in data or not data['author'].strip():
        return jsonify({"error": "Author is required}, 400
    
    # Validate year if provided
    if 'year' in data and data['year'] is not None:
        try:
            year = int(data['year'])
        except ValueError:
            return jsonify({"error": "Year must be a valid integer}, 400
        if year < 0 or year > 2024:
            return jsonify({"error": "Year must be a valid year}, 400

    # Update the book
    cursor.execute('''
        UPDATE books 
        SET title = ?, author = ?, year = ?, isbn = ?
        WHERE id = ?
    ''', (data['title'], data['author'], data.get('year'), data.get('isbn'), book_id))
    
    conn.commit()
    conn.close()
    
    return jsonify({"message": "Book updated successfully}, 200

@app.route('/books/<int:book_id>', methods=['DELETE'])
def delete_book(book_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if book exists
    cursor.execute('SELECT * FROM books WHERE id = ?', (book_id,))
    book = cursor.fetchone()
    
    if book is None:
        abort(404)
    
    # Delete the book
    cursor.execute('DELETE FROM books WHERE id = ?', (book_id,))
    conn.commit()
    conn.close()
    
    return jsonify({"message": "Book deleted successfully}, 200

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)