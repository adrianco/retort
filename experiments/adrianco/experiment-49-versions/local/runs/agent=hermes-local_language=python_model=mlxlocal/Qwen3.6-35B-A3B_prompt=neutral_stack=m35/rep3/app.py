import sqlite3
from flask import Flask, request, jsonify, g, current_app

DATABASE = 'books.db'


def get_db():
    """Get a database connection for the current request."""
    if 'db' not in g:
        g.db = sqlite3.connect(current_app.config['DATABASE'])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA journal_mode=WAL")
    return g.db


def close_db(exception):
    """Close the database connection at the end of the request."""
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db(db_path=None):
    """Initialize the database with the books table."""
    if db_path is None:
        db_path = current_app.config['DATABASE']
    db = sqlite3.connect(db_path)
    db.execute('''
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER,
            isbn TEXT
        )
    ''')
    db.commit()
    db.close()


def create_app(test_config=None):
    """Application factory."""
    app = Flask(__name__)

    if test_config is None:
        app.config.from_mapping(
            DATABASE=DATABASE,
            TESTING=False,
        )
    else:
        app.config.update(test_config)

    app.teardown_appcontext(close_db)

    @app.route('/health', methods=['GET'])
    def health_check():
        return jsonify({'status': 'healthy'}), 200

    @app.route('/books', methods=['POST'])
    def create_book():
        data = request.get_json()

        if not data:
            return jsonify({'error': 'Request body must be JSON'}), 400

        title = data.get('title')
        author = data.get('author')
        year = data.get('year')
        isbn = data.get('isbn')

        if not title or not str(title).strip():
            return jsonify({'error': 'Title is required'}), 400

        if not author or not str(author).strip():
            return jsonify({'error': 'Author is required'}), 400

        db = get_db()
        cursor = db.execute(
            'INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)',
            (str(title).strip(), str(author).strip(), year, isbn)
        )
        db.commit()

        book_id = cursor.lastrowid

        return jsonify({
            'id': book_id,
            'title': str(title).strip(),
            'author': str(author).strip(),
            'year': year,
            'isbn': isbn
        }), 201

    @app.route('/books', methods=['GET'])
    def list_books():
        author_filter = request.args.get('author')

        db = get_db()

        if author_filter:
            books = db.execute(
                'SELECT * FROM books WHERE author LIKE ?',
                (f'%{author_filter}%',)
            ).fetchall()
        else:
            books = db.execute('SELECT * FROM books').fetchall()

        result = [dict(book) for book in books]
        return jsonify(result), 200

    @app.route('/books/<int:book_id>', methods=['GET'])
    def get_book(book_id):
        db = get_db()
        book = db.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()

        if book is None:
            return jsonify({'error': 'Book not found'}), 404

        return jsonify(dict(book)), 200

    @app.route('/books/<int:book_id>', methods=['PUT'])
    def update_book(book_id):
        db = get_db()
        book = db.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()

        if book is None:
            return jsonify({'error': 'Book not found'}), 404

        data = request.get_json()

        if not data:
            return jsonify({'error': 'Request body must be JSON'}), 400

        title = data.get('title', book['title'])
        author = data.get('author', book['author'])
        year = data.get('year', book['year'])
        isbn = data.get('isbn', book['isbn'])

        if not title or not str(title).strip():
            return jsonify({'error': 'Title is required'}), 400

        if not author or not str(author).strip():
            return jsonify({'error': 'Author is required'}), 400

        db.execute(
            'UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?',
            (str(title).strip(), str(author).strip(), year, isbn, book_id)
        )
        db.commit()

        updated_book = db.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()

        return jsonify(dict(updated_book)), 200

    @app.route('/books/<int:book_id>', methods=['DELETE'])
    def delete_book(book_id):
        db = get_db()
        book = db.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()

        if book is None:
            return jsonify({'error': 'Book not found'}), 404

        db.execute('DELETE FROM books WHERE id = ?', (book_id,))
        db.commit()

        return jsonify({'message': 'Book deleted successfully'}), 200

    return app


app = create_app()

if __name__ == '__main__':
    with app.app_context():
        init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)
