"""SQLite-backed book collection REST API."""
import os
import sqlite3

from flask import Flask, g, jsonify, request, url_for
from werkzeug.exceptions import BadRequest, HTTPException, NotFound


def create_app(config=None):
    app = Flask(__name__)
    app.config.from_mapping(DATABASE=os.environ.get('BOOKS_DATABASE', 'books.db'))
    if config:
        app.config.update(config)

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
        db().execute('''CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            year INTEGER,
            isbn TEXT
        )''')
        db().commit()

    @app.errorhandler(HTTPException)
    def http_error(error):
        response = error.get_response()
        response.data = app.json.dumps({'error': error.description})
        response.content_type = 'application/json'
        return response

    def payload():
        data = request.get_json()
        if not isinstance(data, dict):
            raise BadRequest('Request body must be a JSON object.')
        if set(data) - {'title', 'author', 'year', 'isbn'}:
            raise BadRequest('Unknown book fields.')
        for field in ('title', 'author'):
            if not isinstance(data.get(field), str) or not data[field].strip():
                raise BadRequest(f'{field} is required and must be a nonblank string.')
        year = data.get('year')
        if year is not None and (type(year) is not int or not 1 <= year <= 9999):
            raise BadRequest('year must be an integer between 1 and 9999 or null.')
        isbn = data.get('isbn')
        if isbn is not None and (not isinstance(isbn, str) or not isbn.strip()):
            raise BadRequest('isbn must be a nonblank string or null.')
        return (data['title'].strip(), data['author'].strip(), year,
                isbn.strip() if isbn is not None else None)

    def book(book_id):
        validate_book_id(book_id)
        row = db().execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()
        if row is None:
            raise NotFound('Book not found.')
        return dict(row)

    def validate_book_id(book_id):
        # SQLite INTEGER values are signed 64-bit; Flask accepts larger integers.
        if not 1 <= book_id <= 2**63 - 1:
            raise NotFound('Book not found.')

    @app.get('/health')
    def health():
        db().execute('SELECT 1')
        return jsonify(status='ok')

    @app.post('/books')
    def create_book():
        values = payload()
        with db() as connection:
            cursor = connection.execute(
                'INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)', values)
        result = book(cursor.lastrowid)
        return jsonify(result), 201, {'Location': url_for('get_book', book_id=result['id'])}

    @app.get('/books')
    def list_books():
        author = request.args.get('author')
        if author is None:
            rows = db().execute('SELECT * FROM books ORDER BY id')
        else:
            rows = db().execute('SELECT * FROM books WHERE author = ? ORDER BY id', (author,))
        return jsonify([dict(row) for row in rows])

    @app.get('/books/<int:book_id>')
    def get_book(book_id):
        return jsonify(book(book_id))

    @app.put('/books/<int:book_id>')
    def update_book(book_id):
        validate_book_id(book_id)
        values = payload()
        with db() as connection:
            cursor = connection.execute(
                'UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?',
                (*values, book_id))
            if cursor.rowcount == 0:
                raise NotFound('Book not found.')
        return jsonify(book(book_id))

    @app.delete('/books/<int:book_id>')
    def delete_book(book_id):
        validate_book_id(book_id)
        with db() as connection:
            cursor = connection.execute('DELETE FROM books WHERE id = ?', (book_id,))
            if cursor.rowcount == 0:
                raise NotFound('Book not found.')
        return jsonify(message='Book deleted.', id=book_id)

    return app


app = create_app()


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=int(os.environ.get('PORT', '5000')))
