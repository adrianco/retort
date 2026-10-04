"""Dependency-free WSGI book collection API backed by SQLite."""
import argparse
import json
import logging
import os
import re
import sqlite3
from http import HTTPStatus
from urllib.parse import parse_qs
from wsgiref.simple_server import make_server

MAX_BODY = 1024 * 1024


class APIError(Exception):
    def __init__(self, status, message):
        self.status = status
        self.message = message


def read_book(environ):
    if environ.get('CONTENT_TYPE', '').split(';')[0].strip().lower() != 'application/json':
        raise APIError(415, 'Content-Type must be application/json')
    try:
        length = int(environ.get('CONTENT_LENGTH') or 0)
    except ValueError:
        raise APIError(400, 'Invalid Content-Length')
    if length < 0:
        raise APIError(400, 'Invalid Content-Length')
    if length > MAX_BODY:
        raise APIError(413, 'Request body exceeds 1 MiB')
    try:
        data = json.loads(environ['wsgi.input'].read(length))
    except (ValueError, UnicodeDecodeError):
        raise APIError(400, 'Body must be valid JSON')
    if not isinstance(data, dict):
        raise APIError(400, 'Body must be a JSON object')
    if set(data) - {'title', 'author', 'year', 'isbn'}:
        raise APIError(400, 'Unknown book fields')
    for field in ('title', 'author'):
        if not isinstance(data.get(field), str) or not data[field].strip():
            raise APIError(400, f'{field} is required and must be a nonblank string')
    year = data.get('year')
    if year is not None and (type(year) is not int or not 1 <= year <= 9999):
        raise APIError(400, 'year must be an integer between 1 and 9999 or null')
    isbn = data.get('isbn')
    if isbn is not None and (not isinstance(isbn, str) or not isbn.strip()):
        raise APIError(400, 'isbn must be a nonblank string or null')
    return (data['title'].strip(), data['author'].strip(), year,
            isbn.strip() if isbn is not None else None)


class BookAPI:
    def __init__(self, database):
        self.database = os.fspath(database)
        with self.connect() as db:
            db.execute('''CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL, author TEXT NOT NULL,
                year INTEGER, isbn TEXT
            )''')

    def connect(self):
        # Explicitly close each connection; sqlite's context manager only commits.
        from contextlib import closing
        db = sqlite3.connect(self.database, timeout=10)
        db.row_factory = sqlite3.Row
        return closing(db)

    def __call__(self, environ, start_response):
        headers = []
        try:
            status, payload, headers = self.dispatch(environ)
        except APIError as exc:
            status, payload = exc.status, {'error': exc.message}
        except sqlite3.Error:
            logging.exception('Database operation failed')
            status, payload = 500, {'error': 'Database operation failed'}
        body = b'' if status == 204 else json.dumps(payload, ensure_ascii=False).encode('utf-8')
        if status != 204:
            headers.append(('Content-Type', 'application/json; charset=utf-8'))
        headers.append(('Content-Length', str(len(body))))
        start_response(f'{status} {HTTPStatus(status).phrase}', headers)
        return [body]

    def dispatch(self, environ):
        path = environ.get('PATH_INFO', '')
        method = environ['REQUEST_METHOD']
        match = re.fullmatch(r'/books/([1-9][0-9]*)', path)
        allowed = {'/health': ['GET'], '/books': ['GET', 'POST']}.get(path)
        if match:
            allowed = ['GET', 'PUT', 'DELETE']
        if allowed is None:
            raise APIError(404, 'Route not found')
        if method not in allowed:
            return 405, {'error': 'Method not allowed'}, [('Allow', ', '.join(allowed))]
        with self.connect() as db:
            if path == '/health':
                db.execute('SELECT 1')
                return 200, {'status': 'ok'}, []
            if path == '/books':
                if method == 'GET':
                    query = parse_qs(environ.get('QUERY_STRING', ''), keep_blank_values=True)
                    if 'author' in query:
                        rows = db.execute('SELECT * FROM books WHERE author = ? ORDER BY id',
                                          (query['author'][0],)).fetchall()
                    else:
                        rows = db.execute('SELECT * FROM books ORDER BY id').fetchall()
                    return 200, [dict(row) for row in rows], []
                values = read_book(environ)
                with db:
                    cursor = db.execute('INSERT INTO books(title, author, year, isbn) VALUES (?, ?, ?, ?)', values)
                    row = db.execute('SELECT * FROM books WHERE id = ?', (cursor.lastrowid,)).fetchone()
                return 201, dict(row), [('Location', f'/books/{row["id"]}')]
            # Use a string parameter to handle arbitrarily large IDs without overflow.
            book_id = match.group(1)
            row = db.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()
            if row is None:
                raise APIError(404, 'Book not found')
            if method == 'GET':
                return 200, dict(row), []
            if method == 'DELETE':
                with db:
                    db.execute('DELETE FROM books WHERE id = ?', (book_id,))
                return 204, None, []
            values = read_book(environ)
            with db:
                db.execute('UPDATE books SET title = ?, author = ?, year = ?, isbn = ? WHERE id = ?',
                           (*values, book_id))
                row = db.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()
            return 200, dict(row), []


def create_app(database=None):
    return BookAPI(database or os.environ.get('BOOKS_DB', 'books.sqlite3'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8000)
    parser.add_argument('--database', default=os.environ.get('BOOKS_DB', 'books.sqlite3'))
    args = parser.parse_args()
    with make_server(args.host, args.port, create_app(args.database)) as server:
        print(f'Serving on http://{args.host}:{args.port}', flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == '__main__':
    main()
