# Book Collection API

A small REST API for managing books, written with the Python standard library only
(`http.server` + `sqlite3`). No third-party packages are needed to run it; `pytest`
is needed only for the tests.

## Setup

Requires Python 3.9+.

```bash
python3 -m venv venv
venv/bin/pip install -r requirements-dev.txt   # pytest, only needed for tests
```

## Run

```bash
venv/bin/python app.py                       # http://127.0.0.1:8000, data in ./books.db
venv/bin/python app.py --host 0.0.0.0 --port 9000 --db /path/to/books.db
```

## Test

```bash
venv/bin/python -m pytest
```

The tests start the real HTTP server on an ephemeral port against a temporary
SQLite file.

## Endpoints

| Method | Path          | Description                              | Success |
|--------|---------------|------------------------------------------|---------|
| GET    | `/health`     | Health check                             | 200     |
| POST   | `/books`      | Create a book                            | 201     |
| GET    | `/books`      | List books; optional `?author=` filter   | 200     |
| GET    | `/books/{id}` | Get one book                             | 200     |
| PUT    | `/books/{id}` | Replace a book                           | 200     |
| DELETE | `/books/{id}` | Delete a book                            | 204     |

Book fields:

- `title` — string, required, non-empty
- `author` — string, required, non-empty
- `year` — integer, optional
- `isbn` — string, optional

`PUT` is a full replacement: `title` and `author` are required, and omitted optional
fields are set to `null`. The `author` filter is an exact, case-insensitive match.

Errors are JSON: `{"error": "..."}`, with a per-field `details` object for validation
failures. Status codes: 400 (invalid JSON or validation failure), 404 (unknown book or
path), 405 (method not allowed on that path), 411/413 (missing or oversized body).

## Example

```bash
curl -X POST localhost:8000/books -H 'Content-Type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593"}'
curl 'localhost:8000/books?author=Frank%20Herbert'
curl -X PUT localhost:8000/books/1 -H 'Content-Type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1966}'
curl -X DELETE localhost:8000/books/1
```
