"""Book collection JSON API, implemented as a dependency-free WSGI application."""
import json
import os
import re
import sqlite3
from contextlib import contextmanager
from http import HTTPStatus
from urllib.parse import parse_qs
from wsgiref.simple_server import make_server


class APIError(Exception):
    def __init__(self, status, message):
        self.status = status
        self.message = message


class BookAPI:
    def __init__(self, database):
        self.database = str(database)
        with self.connect() as db:
            db.execute('''CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL, author TEXT NOT NULL,
                year INTEGER, isbn TEXT)''')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.database)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def __call__(self, environ, start_response):
        headers = []
        try:
            status, payload, headers = self.dispatch(environ)
        except APIError as exc:
            status, payload = exc.status, {"error": exc.message}
        except sqlite3.Error:
            status, payload = 503, {"error": "Database unavailable"}
        body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        start_response(f'{status} {HTTPStatus(status).phrase}', [
            ('Content-Type', 'application/json; charset=utf-8'),
            ('Content-Length', str(len(body))), *headers])
        return [body]

    def read_book(self, environ):
        if environ.get('CONTENT_TYPE', '').split(';')[0].strip().lower() != 'application/json':
            raise APIError(415, 'Content-Type must be application/json')
        try:
            length = int(environ.get('CONTENT_LENGTH') or 0)
        except ValueError:
            raise APIError(400, 'Invalid Content-Length')
        if length < 0:
            raise APIError(400, 'Invalid Content-Length')
        if length > 1_000_000:
            raise APIError(413, 'Request body too large')
        try:
            data = json.loads(environ['wsgi.input'].read(length))
        except (ValueError, UnicodeError):
            raise APIError(400, 'Request body must be valid JSON')
        if not isinstance(data, dict):
            raise APIError(400, 'Request body must be a JSON object')
        if set(data) - {'title', 'author', 'year', 'isbn'}:
            raise APIError(400, 'Unknown book fields')
        for field in ('title', 'author'):
            if not isinstance(data.get(field), str) or not data[field].strip():
                raise APIError(400, f'{field} is required and must be a nonempty string')
            data[field] = data[field].strip()
        year = data.get('year')
        if year is not None and (type(year) is not int or not -9223372036854775808 <= year <= 9223372036854775807):
            raise APIError(400, 'year must be an integer or null within SQLite integer range')
        if data.get('isbn') is not None and not isinstance(data['isbn'], str):
            raise APIError(400, 'isbn must be a string or null')
        return (data['title'], data['author'], year, data.get('isbn'))

    def dispatch(self, env):
        path, method = env.get('PATH_INFO', '/'), env['REQUEST_METHOD']
        if path == '/health':
            if method != 'GET':
                return 405, {'error': 'Method not allowed'}, [('Allow', 'GET')]
            with self.connect() as db:
                db.execute('SELECT 1')
            return 200, {'status': 'ok'}, []
        match = re.fullmatch(r'/books/([0-9]+)', path)
        if path != '/books' and not match:
            raise APIError(404, 'Route not found')
        allowed = 'GET, PUT, DELETE' if match else 'GET, POST'
        if method not in allowed.split(', '):
            return 405, {'error': 'Method not allowed'}, [('Allow', allowed)]
        if match and len(match[1].lstrip('0')) > 19:
            raise APIError(404, 'Book not found')
        book_id = int(match[1].lstrip('0') or '0') if match else None
        if book_id is not None and book_id > 9223372036854775807:
            raise APIError(404, 'Book not found')
        with self.connect() as db:
            if match:
                book = db.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()
                if book is None:
                    raise APIError(404, 'Book not found')
                if method == 'GET':
                    return 200, dict(book), []
                if method == 'DELETE':
                    db.execute('DELETE FROM books WHERE id = ?', (book_id,))
                    return 200, {'deleted': book_id}, []
                values = self.read_book(env)
                db.execute('UPDATE books SET title=?, author=?, year=?, isbn=? WHERE id=?', (*values, book_id))
            elif method == 'GET':
                params = parse_qs(env.get('QUERY_STRING', ''), keep_blank_values=True)
                if 'author' in params:
                    rows = db.execute('SELECT * FROM books WHERE author = ? ORDER BY id', (params['author'][0],)).fetchall()
                else:
                    rows = db.execute('SELECT * FROM books ORDER BY id').fetchall()
                return 200, [dict(row) for row in rows], []
            else:
                values = self.read_book(env)
                book_id = db.execute('INSERT INTO books (title, author, year, isbn) VALUES (?, ?, ?, ?)', values).lastrowid
            book = dict(db.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone())
            return (201, book, [('Location', f'/books/{book_id}')]) if method == 'POST' else (200, book, [])


def create_app(database=None):
    return BookAPI(database or os.environ.get('BOOKS_DB', 'books.db'))


if __name__ == '__main__':
    application = create_app()
    host, port = os.environ.get('HOST', '127.0.0.1'), int(os.environ.get('PORT', '8000'))
    with make_server(host, port, application) as server:
        print(f'Serving on http://{host}:{port}', flush=True)
        server.serve_forever()
