# Book Collection API

A small REST API for managing a book collection, storing its data in SQLite.

It uses only the Python standard library (`wsgiref` + `sqlite3`), so there is
nothing to install to run it. `pytest` is needed only for the tests.

## Setup

Requires Python 3.9 or newer.

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt   # only needed to run the tests
```

## Run

```bash
python app.py
```

The server listens on `http://127.0.0.1:8000` and creates `books.db` in the
current directory. Both can be changed with environment variables:

| Variable   | Default     | Purpose                      |
|------------|-------------|------------------------------|
| `HOST`     | `127.0.0.1` | Address to bind to           |
| `PORT`     | `8000`      | Port to listen on            |
| `BOOKS_DB` | `books.db`  | Path to the SQLite database  |

The bundled `wsgiref` server handles one request at a time and is meant for
local use. `app.create_app(db_path)` returns a standard WSGI application, so it
can be served by any WSGI server instead.

## Test

```bash
python -m pytest
```

The tests call the WSGI app in-process against a temporary database, plus one
end-to-end test over a real HTTP socket.

## API

A book looks like this:

```json
{"id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593"}
```

| Method | Path          | Description                  | Success | Errors   |
|--------|---------------|------------------------------|---------|----------|
| GET    | `/health`     | Health check                 | 200     |          |
| POST   | `/books`      | Create a book                | 201     | 400      |
| GET    | `/books`      | List books (`?author=` filter) | 200   |          |
| GET    | `/books/{id}` | Get one book                 | 200     | 404      |
| PUT    | `/books/{id}` | Replace a book               | 200     | 400, 404 |
| DELETE | `/books/{id}` | Delete a book                | 204     | 404      |

Unknown paths return 404, unsupported methods return 405 with an `Allow`
header, and request bodies over 1 MB return 413.

### Fields

| Field    | Type    | Rules                                        |
|----------|---------|----------------------------------------------|
| `title`  | string  | Required, must not be blank                  |
| `author` | string  | Required, must not be blank                  |
| `year`   | integer | Optional, between -9999 and 9999             |
| `isbn`   | string  | Optional; format and uniqueness not checked  |

Leading and trailing whitespace is trimmed from strings. Unknown fields are
ignored.

### Behaviour worth knowing

- `PUT` replaces the whole book: `title` and `author` are required again, and
  an omitted `year` or `isbn` is reset to `null`.
- `?author=` matches the full author name, ignoring case (ASCII letters only).
  It is not a substring search.
- Errors are JSON: `{"error": "..."}`. Validation failures also list each
  offending field under `details`.

### Examples

```bash
curl -X POST localhost:8000/books \
  -H 'Content-Type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593"}'

curl 'localhost:8000/books?author=Frank%20Herbert'
curl localhost:8000/books/1

curl -X PUT localhost:8000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1966}'

curl -X DELETE localhost:8000/books/1
curl localhost:8000/health
```
