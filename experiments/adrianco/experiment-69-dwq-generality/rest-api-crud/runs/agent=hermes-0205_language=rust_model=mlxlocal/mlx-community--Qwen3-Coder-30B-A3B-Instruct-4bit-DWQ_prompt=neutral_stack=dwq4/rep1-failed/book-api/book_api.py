#!/usr/bin/env python3
"""
Book API REST Service Implementation in Python
This implements the requirements for managing a book collection via a REST API.
"""

import sqlite3
import os
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# Initialize Flask app
app = Flask(__name__)

# Configure database
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'books.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db = SQLAlchemy(app)

# Book model
class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    author = db.Column(db.String(200), nullable=False)
    year = db.Column(db.Integer)
    isbn = db.Column(db.String(20))
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'author': self.author,
            'year': self.year,
            'isbn': self.isbn
        }

# Create tables
with app.app_context():
    db.create_all()

# Helper function to validate required fields
def validate_book_input(data):
    if not data.get('title') or not data['title'].strip():
        return False, "Title is required"
    if not data.get('author') or not data['author'].strip():
        return False, "Author is required"
    return True, None

# API Routes

@app.route('/books', methods=['POST'])
def create_book():
    data = request.get_json()
    
    # Validate input
    is_valid, error_msg = validate_book_input(data)
    if not is_valid:
        return jsonify({'error': error_msg}), 400
    
    # Create new book
    new_book = Book(
        title=data['title'],
        author=data['author'],
        year=data.get('year'),
        isbn=data.get('isbn')
    )
    
    try:
        db.session.add(new_book)
        db.session.commit()
        return jsonify(new_book.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Database error'}), 500

@app.route('/books', methods=['GET'])
def get_books():
    # Handle author filter
    author = request.args.get('author')
    
    if author:
        books = Book.query.filter(Book.author.contains(author)).all()
    else:
        books = Book.query.all()
    
    return jsonify([book.to_dict() for book in books])

@app.route('/books/<int:book_id>', methods=['GET'])
def get_book(book_id):
    book = Book.query.get_or_404(book_id)
    return jsonify(book.to_dict())

@app.route('/books/<int:book_id>', methods=['PUT'])
def update_book(book_id):
    data = request.get_json()
    
    # Validate input
    is_valid, error_msg = validate_book_input(data)
    if not is_valid:
        return jsonify({'error': error_msg}), 400
    
    book = Book.query.get_or_404(book_id)
    
    # Update book fields
    book.title = data['title']
    book.author = data['author']
    book.year = data.get('year')
    book.isbn = data.get('isbn')
    
    try:
        db.session.commit()
        return jsonify(book.to_dict())
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Database error'}), 500

@app.route('/books/<int:book_id>', methods=['DELETE'])
def delete_book(book_id):
    book = Book.query.get_or_404(book_id)
    
    try:
        db.session.delete(book)
        db.session.commit()
        return '', 204
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Database error'}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'OK'})

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=3000, debug=True)