# Book Collection API

A small REST API for managing a book collection, built with Flask and backed by
SQLite. Books have a `title` (required), `author` (required), `year` (optional
integer), and `isbn` (optional string).

## Setup

Requires Python 3.10+.

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Run

```sh
.venv/bin/python app.py
```

The server listens on `http://127.0.0.1:5000`. Data is stored in `books.db`
next to `app.py` (created automatically on first start). Set the `BOOKS_DB`
environment variable to use a different database file:

```sh
BOOKS_DB=/tmp/mybooks.db .venv/bin/python app.py
```

## Run the tests

```sh
.venv/bin/python -m pytest -v
```

Tests run against a temporary database, so they never touch `books.db`.

## API

| Method | Path          | Description                                      |
|--------|---------------|--------------------------------------------------|
| GET    | `/health`     | Health check                                     |
| POST   | `/books`      | Create a book                                    |
| GET    | `/books`      | List books; optional `?author=` filter           |
| GET    | `/books/{id}` | Get one book                                     |
| PUT    | `/books/{id}` | Replace a book (same validation as create)       |
| DELETE | `/books/{id}` | Delete a book                                    |

All responses are JSON. Validation failures return `400` with an `errors`
object keyed by field name; unknown books and routes return `404` with an
`error` message. `PUT` is a full replacement: omitting `year` or `isbn` clears
them. The `?author=` filter is an exact, case-insensitive match.

### Examples

Health check:

```sh
curl http://127.0.0.1:5000/health
# {"status": "ok"}
```

Create a book (`201 Created`, with a `Location` header):

```sh
curl -X POST http://127.0.0.1:5000/books \
  -H 'Content-Type: application/json' \
  -d '{"title": "Beloved", "author": "Toni Morrison", "year": 1987, "isbn": "978-1400033416"}'
# {"author": "Toni Morrison", "id": 1, "isbn": "978-1400033416", "title": "Beloved", "year": 1987}
```

Validation error (`400 Bad Request`):

```sh
curl -X POST http://127.0.0.1:5000/books \
  -H 'Content-Type: application/json' -d '{"year": 1987}'
# {"errors": {"author": "author is required and must be a non-empty string",
#             "title": "title is required and must be a non-empty string"}}
```

List, optionally filtered by author:

```sh
curl http://127.0.0.1:5000/books
curl 'http://127.0.0.1:5000/books?author=Toni%20Morrison'
```

Get, update, delete:

```sh
curl http://127.0.0.1:5000/books/1
curl -X PUT http://127.0.0.1:5000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title": "Beloved", "author": "Toni Morrison", "year": 1988}'
curl -X DELETE http://127.0.0.1:5000/books/1   # 204 No Content
```

## Project layout

| File          | Purpose                                        |
|---------------|------------------------------------------------|
| `app.py`      | Flask app factory, routes, and validation      |
| `db.py`       | SQLite connection handling and schema          |
| `test_app.py` | Integration tests (pytest + Flask test client) |
