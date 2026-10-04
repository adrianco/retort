"""Flask REST API for a persistent book collection."""
import os
import sqlite3

from flask import Flask, g, jsonify, request, url_for
from werkzeug.exceptions import BadRequest, HTTPException, NotFound


def create_app(database_path=None):
    app = Flask(__name__)
    app.config['DATABASE'] = str(database_path or os.environ.get('BOOKS_DATABASE', 'books.db'))

    def db():
        if 'db' not in g:
            g.db = sqlite3.connect(app.config['DATABASE'])
            g.db.row_factory = sqlite3.Row
        return g.db

    @app.teardown_appcontext
    def close_db(error=None):
        connection = g.pop('db', None)
        if connection is not None:
            connection.close()

    with app.app_context():
        with db() as connection:
            connection.execute('''CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                year INTEGER,
                isbn TEXT
            )''')

    @app.errorhandler(HTTPException)
    def http_error(error):
        response = error.get_response()
        response.data = app.json.dumps({'error': error.description})
        response.content_type = 'application/json'
        return response

    def validate_book():
        payload = request.get_json()
        if not isinstance(payload, dict):
            raise BadRequest('Body must be a JSON object.')
        unknown = set(payload) - {'title', 'author', 'year', 'isbn'}
        if unknown:
            raise BadRequest('Unknown fields: ' + ', '.join(sorted(unknown)))
        for field in ('title', 'author'):
            if not isinstance(payload.get(field), str) or not payload[field].strip():
                raise BadRequest(f'{field} must be a non-empty string.')
        year = payload.get('year')
        if year is not None and (type(year) is not int or not 1 <= year <= 9999):
            raise BadRequest('year must be an integer between 1 and 9999 or null.')
        isbn = payload.get('isbn')
        if isbn is not None and (not isinstance(isbn, str) or not isbn.strip()):
            raise BadRequest('isbn must be a non-empty string or null.')
        return (payload['title'].strip(), payload['author'].strip(), year,
                isbn.strip() if isbn is not None else None)

    def get_book_or_404(book_id):
        book = db().execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()
        if book is None:
            raise NotFound('Book not found.')
        return dict(book)

    @app.get('/health')
    def health():
        db().execute('SELECT 1').fetchone()
        return jsonify(status='ok')

    @app.post('/books')
    def create_book():
        values = validate_book()
        with db() as connection:
            cursor = connection.execute(
                'INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)', values)
        book = get_book_or_404(cursor.lastrowid)
        return jsonify(book), 201, {'Location': url_for('get_book', book_id=book['id'])}

    @app.get('/books')
    def list_books():
        author = request.args.get('author')
        if author is None:
            rows = db().execute('SELECT * FROM books ORDER BY id').fetchall()
        else:
            rows = db().execute('SELECT * FROM books WHERE author = ? ORDER BY id',
                                (author,)).fetchall()
        return jsonify([dict(row) for row in rows])

    @app.get('/books/<int:book_id>')
    def get_book(book_id):
        return jsonify(get_book_or_404(book_id))

    @app.put('/books/<int:book_id>')
    def update_book(book_id):
        get_book_or_404(book_id)
        values = validate_book()
        with db() as connection:
            cursor = connection.execute(
                'UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?',
                (*values, book_id))
            if not cursor.rowcount:
                raise NotFound('Book not found.')
        return jsonify(get_book_or_404(book_id))

    @app.delete('/books/<int:book_id>')
    def delete_book(book_id):
        with db() as connection:
            cursor = connection.execute('DELETE FROM books WHERE id = ?', (book_id,))
            if not cursor.rowcount:
                raise NotFound('Book not found.')
        return jsonify(id=book_id, deleted=True), 200

    return app


if __name__ == '__main__':
    create_app().run(host='127.0.0.1', port=int(os.environ.get('PORT', '5000')))
