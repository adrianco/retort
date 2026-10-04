# Book Collection API

A small REST API for managing a book collection. It uses only the Python
standard library (`http.server` + `sqlite3`), so there is nothing to install to
run it. Data is stored in a SQLite file.

## Requirements

- Python 3.10+
- `pytest` (only for running the tests)

## Run

```bash
python3 app.py
```

The server listens on `http://127.0.0.1:8000` by default. Configure it with
environment variables:

| Variable        | Default     | Description               |
|-----------------|-------------|---------------------------|
| `HOST`          | `127.0.0.1` | Interface to bind         |
| `PORT`          | `8000`      | Port to listen on         |
| `DATABASE_PATH` | `books.db`  | SQLite database file path |

## Endpoints

| Method | Path          | Description                          | Success |
|--------|---------------|--------------------------------------|---------|
| GET    | `/health`     | Health check                         | 200     |
| POST   | `/books`      | Create a book                        | 201     |
| GET    | `/books`      | List books (optional `?author=`)     | 200     |
| GET    | `/books/{id}` | Get one book                         | 200     |
| PUT    | `/books/{id}` | Replace a book                       | 200     |
| DELETE | `/books/{id}` | Delete a book                        | 204     |

A book looks like:

```json
{"id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}
```

Validation rules:

- `title` and `author` are required, non-empty strings.
- `year` is optional and must be an integer.
- `isbn` is optional and must be a string.
- `PUT` replaces the whole book, so it needs `title` and `author` too; omitted
  optional fields are reset to `null`.
- The `?author=` filter is an exact, case-insensitive match.

Errors are returned as JSON, e.g. `400`:

```json
{"error": "validation failed", "details": {"title": "is required"}}
```

Other error statuses: `404` (unknown book or route), `405` (method not allowed
on a known route), `411` (missing `Content-Length`), `413` (body over 1 MB).

## Examples

```bash
curl -X POST localhost:8000/books -H 'Content-Type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441172719"}'
curl localhost:8000/books
curl 'localhost:8000/books?author=Frank%20Herbert'
curl localhost:8000/books/1
curl -X PUT localhost:8000/books/1 -H 'Content-Type: application/json' \
  -d '{"title": "Dune Messiah", "author": "Frank Herbert", "year": 1969}'
curl -X DELETE localhost:8000/books/1
curl localhost:8000/health
```

## Tests

```bash
python3 -m venv venv            # skip if venv/ already exists
venv/bin/pip install -r requirements-dev.txt
venv/bin/python -m pytest
```

The tests start the real server on an ephemeral port against an in-memory
SQLite database.
