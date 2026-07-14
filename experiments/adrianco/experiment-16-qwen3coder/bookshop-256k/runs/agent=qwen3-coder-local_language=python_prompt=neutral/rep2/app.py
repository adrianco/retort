from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

# Initialize Flask app
app = Flask(__name__)

# Configure SQLite database
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
    year = db.Column(db.Integer, nullable=True)
    isbn = db.Column(db.String(20), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'author': self.author,
            'year': self.year,
            'isbn': self.isbn,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

# Create tables
with app.app_context():
    db.create_all()

# Health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy'}), 200

# POST /books - Create a new book
@app.route('/books', methods=['POST'])
def create_book():
    data = request.get_json()
    
    # Validate required fields
    if not data or 'title' not in data or 'author' not in data:
        return jsonify({'error': 'Title and author are required'}), 400
    
    # Create new book
    book = Book(
        title=data['title'],
        author=data['author'],
        year=data.get('year'),
        isbn=data.get('isbn')
    )
    
    try:
        db.session.add(book)
        db.session.commit()
        return jsonify(book.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to create book'}), 500

# GET /books - List all books with optional author filter
@app.route('/books', methods=['GET'])
def get_books():
    author = request.args.get('author')
    
    if author:
        books = Book.query.filter_by(author=author).all()
    else:
        books = Book.query.all()
    
    return jsonify([book.to_dict() for book in books]), 200

# GET /books/{id} - Get a single book by ID
@app.route('/books/<int:book_id>', methods=['GET'])
def get_book(book_id):
    book = Book.query.get_or_404(book_id)
    return jsonify(book.to_dict()), 200

# PUT /books/{id} - Update a book
@app.route('/books/<int:book_id>', methods=['PUT'])
def update_book(book_id):
    book = Book.query.get_or_404(book_id)
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    # Update fields if provided
    if 'title' in data:
        book.title = data['title']
    if 'author' in data:
        book.author = data['author']
    if 'year' in data:
        book.year = data['year']
    if 'isbn' in data:
        book.isbn = data['isbn']
    
    try:
        db.session.commit()
        return jsonify(book.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to update book'}), 500

# DELETE /books/{id} - Delete a book
@app.route('/books/<int:book_id>', methods=['DELETE'])
def delete_book(book_id):
    book = Book.query.get_or_404(book_id)
    
    try:
        db.session.delete(book)
        db.session.commit()
        return jsonify({'message': 'Book deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to delete book'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)