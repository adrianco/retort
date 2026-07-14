from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)

# Configure SQLite database
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(basedir, "books.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


class Book(db.Model):
    __tablename__ = 'books'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    author = db.Column(db.String(200), nullable=False)
    year = db.Column(db.Integer, nullable=True)
    isbn = db.Column(db.String(20), nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'author': self.author,
            'year': self.year,
            'isbn': self.isbn,
        }


def init_db():
    """Create tables if they don't exist."""
    with app.app_context():
        db.create_all()


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({'status': 'healthy'}), 200


@app.route('/books', methods=['POST'])
def create_book():
    """Create a new book."""
    data = request.get_json()

    if not data:
        return jsonify({'error': 'Request body must be JSON'}), 400

    title = data.get('title')
    author = data.get('author')

    if not title or not title.strip():
        return jsonify({'error': 'Title is required'}), 400

    if not author or not author.strip():
        return jsonify({'error': 'Author is required'}), 400

    year = data.get('year')
    isbn = data.get('isbn')

    # Validate year if provided
    if year is not None:
        try:
            year = int(year)
        except (ValueError, TypeError):
            return jsonify({'error': 'Year must be an integer'}), 400

    book = Book(title=title.strip(), author=author.strip(), year=year, isbn=isbn)
    db.session.add(book)
    db.session.commit()

    return jsonify(book.to_dict()), 201


@app.route('/books', methods=['GET'])
def list_books():
    """List all books, with optional author filter."""
    author = request.args.get('author')

    with app.app_context():
        if author:
            books = Book.query.filter(
                db.func.lower(Book.author) == author.lower()
            ).all()
        else:
            books = Book.query.all()

        return jsonify([book.to_dict() for book in books]), 200


@app.route('/books/<int:book_id>', methods=['GET'])
def get_book(book_id):
    """Get a single book by ID."""
    book = db.session.get(Book, book_id)

    if not book:
        return jsonify({'error': 'Book not found'}), 404

    return jsonify(book.to_dict()), 200


@app.route('/books/<int:book_id>', methods=['PUT'])
def update_book(book_id):
    """Update a book."""
    book = db.session.get(Book, book_id)

    if not book:
        return jsonify({'error': 'Book not found'}), 404

    data = request.get_json()

    if not data:
        return jsonify({'error': 'Request body must be JSON'}), 400

    if 'title' in data:
        if not data['title'].strip():
            return jsonify({'error': 'Title cannot be empty'}), 400
        book.title = data['title'].strip()

    if 'author' in data:
        if not data['author'].strip():
            return jsonify({'error': 'Author cannot be empty'}), 400
        book.author = data['author'].strip()

    if 'year' in data:
        try:
            book.year = int(data['year'])
        except (ValueError, TypeError):
            return jsonify({'error': 'Year must be an integer'}), 400

    if 'isbn' in data:
        book.isbn = data['isbn']

    db.session.commit()

    return jsonify(book.to_dict()), 200


@app.route('/books/<int:book_id>', methods=['DELETE'])
def delete_book(book_id):
    """Delete a book."""
    book = db.session.get(Book, book_id)

    if not book:
        return jsonify({'error': 'Book not found'}), 404

    db.session.delete(book)
    db.session.commit()

    return jsonify({'message': 'Book deleted successfully'}), 200


# Initialize the database on import
init_db()


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
