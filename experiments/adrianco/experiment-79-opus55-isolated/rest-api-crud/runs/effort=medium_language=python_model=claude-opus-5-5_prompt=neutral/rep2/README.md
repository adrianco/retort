# Book Collection API

A small REST API for managing a book collection, backed by SQLite.

It uses only the Python standard library (`http.server` + `sqlite3`), so there is
nothing to install to run it. `pytest` is needed only for the tests.

## Setup

Requires Python 3.9+.

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt   # only needed to run the tests
```

## Run

```bash
python app.py
```

The server listens on `http://127.0.0.1:8000` and stores data in `books.db` in the
current directory. Both are configurable through environment variables:

| Variable   | Default     | Purpose                   |
|------------|-------------|---------------------------|
| `HOST`     | `127.0.0.1` | Address to bind           |
| `PORT`     | `8000`      | Port to listen on         |
| `BOOKS_DB` | `books.db`  | Path to the SQLite file   |

```bash
PORT=9000 BOOKS_DB=/tmp/books.db python app.py
```

## Test

```bash
python -m pytest
```

The tests start a real server on an ephemeral port with a temporary database, so
they do not touch `books.db`.

## API

A book looks like this:

```json
{"id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}
```

| Method | Path          | Description                           | Success | Errors        |
|--------|---------------|---------------------------------------|---------|---------------|
| GET    | `/health`     | Health check, returns `{"status": "ok"}` | 200  |               |
| POST   | `/books`      | Create a book                         | 201     | 400, 413      |
| GET    | `/books`      | List books, optional `?author=` filter | 200    |               |
| GET    | `/books/{id}` | Get one book                          | 200     | 404           |
| PUT    | `/books/{id}` | Replace a book                        | 200     | 400, 404, 413 |
| DELETE | `/books/{id}` | Delete a book (empty response body)   | 204     | 404           |

Unknown paths return 404 and unsupported methods return 405 with an `Allow` header.

### Validation

- `title` and `author` are required, non-empty strings (surrounding whitespace is trimmed).
- `year` is optional and must be an integer.
- `isbn` is optional and must be a string.
- `PUT` replaces the whole book: `title` and `author` are required again, and an
  omitted `year` or `isbn` is reset to `null`.
- `?author=` matches the full author name, case-insensitively.

Errors are JSON. Validation failures list each offending field:

```json
{"error": "Validation failed", "details": {"title": "title is required"}}
```

### Examples

```bash
curl -X POST localhost:8000/books \
  -H 'Content-Type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}'

curl localhost:8000/books
curl 'localhost:8000/books?author=Frank%20Herbert'
curl localhost:8000/books/1

curl -X PUT localhost:8000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1966}'

curl -X DELETE localhost:8000/books/1
curl localhost:8000/health
```
