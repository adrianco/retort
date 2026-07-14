import sqlite3
import os

from flask import Flask, request, jsonify, g


def create_app(database_path=None):
    """Application factory for creating the Flask app."""
    if database_path is None:
        database_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'books.db')

    app = Flask(__name__)
    app.config['DATABASE'] = database_path

    def get_db():
        if 'db' not in g:
            db = sqlite3.connect(database_path)
            db.row_factory = sqlite3.Row
            g.db = db
        return g.db

    @app.teardown_appcontext
    def close_db(exception):
        db = g.pop('db', None)
        if db is not None:
            db.close()

    def init_db():
        conn = sqlite3.connect(database_path)
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

    def book_to_dict(row):
        return {
            'id': row['id'],
            'title': row['title'],
            'author': row['author'],
            'year': row['year'],
            'isbn': row['isbn']
        }

    # Initialize the database immediately so it exists on import
    init_db()

    @app.route('/health', methods=['GET'])
    def health():
        return jsonify({'status': 'healthy'}), 200

    @app.route('/books', methods=['POST'])
    def create_book():
        data = request.get_json(silent=True)

        if not data:
            return jsonify({'error': 'Request body must be JSON'}), 400

        title = data.get('title')
        author = data.get('author')
        year = data.get('year')
        isbn = data.get('isbn')

        if not title or not isinstance(title, str) or title.strip() == '':
            return jsonify({'error': 'title is required and must be a non-empty string'}), 400

        if not author or not isinstance(author, str) or author.strip() == '':
            return jsonify({'error': 'author is required and must be a non-empty string'}), 400

        if year is not None:
            try:
                year = int(year)
            except (ValueError, TypeError):
                return jsonify({'error': 'year must be a valid integer'}), 400

        db = get_db()
        try:
            cursor = db.execute(
                'INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)',
                (title.strip(), author.strip(), year if year is not None else None, isbn)
            )
            db.commit()
            book_id = cursor.lastrowid

            new_book = db.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()
            return jsonify(book_to_dict(new_book)), 201

        except sqlite3.IntegrityError:
            return jsonify({'error': 'A book with this ISBN already exists'}), 409

    @app.route('/books', methods=['GET'])
    def list_books():
        db = get_db()
        author_filter = request.args.get('author')

        if author_filter:
            books = db.execute(
                'SELECT * FROM books WHERE author LIKE ?', ('%' + author_filter + '%',)
            ).fetchall()
        else:
            books = db.execute('SELECT * FROM books').fetchall()

        return jsonify([book_to_dict(book) for book in books]), 200

    @app.route('/books/<int:book_id>', methods=['GET'])
    def get_book(book_id):
        db = get_db()
        book = db.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()

        if book is None:
            return jsonify({'error': 'Book not found'}), 404

        return jsonify(book_to_dict(book)), 200

    @app.route('/books/<int:book_id>', methods=['PUT'])
    def update_book(book_id):
        db = get_db()
        existing_book = db.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()

        if existing_book is None:
            return jsonify({'error': 'Book not found'}), 404

        data = request.get_json(silent=True)
        if not data:
            return jsonify({'error': 'Request body must be JSON'}), 400

        title = data.get('title', existing_book['title'])
        author = data.get('author', existing_book['author'])

        if not title or not isinstance(title, str) or title.strip() == '':
            return jsonify({'error': 'title is required and must be a non-empty string'}), 400

        if not author or not isinstance(author, str) or author.strip() == '':
            return jsonify({'error': 'author is required and must be a non-empty string'}), 400

        year = data.get('year', existing_book['year'])
        isbn = data.get('isbn', existing_book['isbn'])

        if year is not None:
            try:
                year = int(year)
            except (ValueError, TypeError):
                return jsonify({'error': 'year must be a valid integer'}), 400

        try:
            db.execute(
                'UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?',
                (title.strip(), author.strip(), year if year is not None else None, isbn, book_id)
            )
            db.commit()

            updated_book = db.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()
            return jsonify(book_to_dict(updated_book)), 200

        except sqlite3.IntegrityError:
            return jsonify({'error': 'A book with this ISBN already exists'}), 409

    @app.route('/books/<int:book_id>', methods=['DELETE'])
    def delete_book(book_id):
        db = get_db()
        existing_book = db.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()

        if existing_book is None:
            return jsonify({'error': 'Book not found'}), 404

        db.execute('DELETE FROM books WHERE id = ?', (book_id,))
        db.commit()

        return jsonify({'message': 'Book deleted successfully'}), 200

    return app


app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
