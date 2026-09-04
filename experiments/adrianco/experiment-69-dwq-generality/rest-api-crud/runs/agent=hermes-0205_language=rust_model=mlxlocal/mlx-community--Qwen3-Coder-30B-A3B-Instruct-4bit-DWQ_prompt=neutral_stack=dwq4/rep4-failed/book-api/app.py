#!/usr/bin/env python3
"""
Book API REST Service Implementation in Python
==============================================

This is a Python-based REST API service for managing a book collection.
It provides all the required endpoints with SQLite database backend.
"""

import sqlite3
import json
from flask import Flask, request, jsonify
from typing import Optional, List
import os

app = Flask(__name__)

# Database initialization
def init_db():
    """Initialize the SQLite database with the books table."""
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

# Helper functions
def get_db_connection():
    """Create and return a database connection."""
    conn = sqlite3.connect('books.db')
    conn.row_factory = sqlite3.Row
    return conn

def book_to_dict(book) -> dict:
    """Convert a book row to a dictionary."""
    return {
        'id': book['id'],
        'title': book['title'],
        'author': book['author'],
        'year': book['year'],
        'isbn': book['isbn']
    }

# Routes
@app.route('/books', methods=['POST'])
def create_book():
    """Create a new book."""
    data = request.get_json()
    
    # Validate required fields
    if not data or 'title' not in data or 'author' not in data:
        return jsonify({'error': 'Title and author are required'}), 400
    
    if not data['title'].strip():
        return jsonify({'error': 'Title is required'}), 400
    
    if not data['author'].strip():
        return jsonify({'error': 'Author is required'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            'INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)',
            (data['title'], data['author'], data.get('year'), data.get('isbn'))
        )
        conn.commit()
        book_id = cursor.lastrowid
        
        # Retrieve the created book
        cursor.execute('SELECT * FROM books WHERE id = ?', (book_id,))
        book = cursor.fetchone()
        
        conn.close()
        return jsonify(book_to_dict(book)), 201
    except Exception as e:
        conn.close()
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/books', methods=['GET'])
def get_books():
    """Get all books (with optional author filter)."""
    author = request.args.get('author')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if author:
        cursor.execute('SELECT * FROM books WHERE author = ?', (author,))
    else:
        cursor.execute('SELECT * FROM books')
    
    books = cursor.fetchall()
    conn.close()
    
    return jsonify([book_to_dict(book) for book in books])

@app.route('/books/<int:id>', methods=['GET'])
def get_book_by_id(id):
    """Get a single book by ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM books WHERE id = ?', (id,))
    book = cursor.fetchone()
    conn.close()
    
    if book is None:
        return jsonify({'error': 'Book not found'}), 404
    
    return jsonify(book_to_dict(book))

@app.route('/books/<int:id>', methods=['PUT'])
def update_book(id):
    """Update a book."""
    data = request.get_json()
    
    # Validate required fields
    if not data or 'title' not in data or 'author' not in data:
        return jsonify({'error': 'Title and author are required'}), 400
    
    if not data['title'].strip():
        return jsonify({'error': 'Title is required'}), 400
    
    if not data['author'].strip():
        return jsonify({'error': 'Author is required'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            'UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?',
            (data['title'], data['author'], data.get('year'), data.get('isbn'), id)
        )
        
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({'error': 'Book not found'}), 404
        
        conn.commit()
        
        # Retrieve the updated book
        cursor.execute('SELECT * FROM books WHERE id = ?', (id,))
        book = cursor.fetchone()
        conn.close()
        
        return jsonify(book_to_dict(book))
    except Exception as e:
        conn.close()
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/books/<int:id>', methods=['DELETE'])
def delete_book(id):
    """Delete a book."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('DELETE FROM books WHERE id = ?', (id,))
        
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({'error': 'Book not found'}), 404
        
        conn.commit()
        conn.close()
        return '', 204
    except Exception as e:
        conn.close()
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({'status': 'OK'})

# Main function to run the application
if __name__ == '__main__':
    # Initialize the database
    init_db()
    
    # Run the Flask application
    app.run(host='127.0.0.1', port=8080, debug=True)