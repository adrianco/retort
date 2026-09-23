# Book Collection API

A REST API for managing a book collection, written in Python with SQLite storage.
It uses only the standard library (`http.server` + `sqlite3`), so running the
service needs no third-party packages. `pytest` is only needed for the tests.

## Requirements

- Python 3.10+
- `pytest` (for the tests only)

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt
```

## Run

```bash
python app.py                      # http://127.0.0.1:8000, data in ./books.db
python app.py --port 9000 --db /tmp/books.db
python app.py --host 0.0.0.0 --db :memory:   # ephemeral in-memory database
```

You can also set these with the `HOST`, `PORT` and `BOOKS_DB` environment variables.

## Test

```bash
pytest -v
```

The suite has unit tests for validation and the SQLite repository, plus
integration tests that start the real HTTP server on a random port and call
every endpoint.

## Endpoints

| Method | Path            | Description                               | Success |
|--------|-----------------|-------------------------------------------|---------|
| GET    | `/health`       | Health check (includes a database ping)   | 200     |
| POST   | `/books`        | Create a book                             | 201     |
| GET    | `/books`        | List books; `?author=` filters by author  | 200     |
| GET    | `/books/{id}`   | Get one book                              | 200     |
| PUT    | `/books/{id}`   | Replace a book                            | 200     |
| DELETE | `/books/{id}`   | Delete a book                             | 204     |

### Book fields

| Field    | Type    | Rules                                                              |
|----------|---------|--------------------------------------------------------------------|
| `title`  | string  | **Required**, non-empty, at most 500 characters (whitespace is trimmed) |
| `author` | string  | **Required**, non-empty, at most 300 characters (whitespace is trimmed) |
| `year`   | integer | Optional; must be between -5000 and next year                     |
| `isbn`   | string  | Optional; a valid ISBN-10 or ISBN-13, unique across books. Hyphens and spaces are removed before it's stored |

`id` is assigned by the server. `PUT` replaces the whole record, so send every
field you want to keep; any optional field you leave out is cleared. The
`?author=` filter is an exact match that ignores case.

### Errors

Errors come back as JSON:

```json
{"error": "Validation failed", "details": {"title": "is required"}}
```

| Status | When                                                     |
|--------|----------------------------------------------------------|
| 400    | Missing, empty or invalid JSON body, or failed validation |
| 404    | Book or route not found                                  |
| 405    | Method not supported on that path (see the `Allow` header) |
| 409    | ISBN already belongs to another book                     |
| 413    | Request body larger than 1 MB                            |
| 500    | Unexpected server error                                  |

## Examples

```bash
curl -X POST localhost:8000/books -H 'Content-Type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441013593"}'
# 201 {"id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593"}

curl 'localhost:8000/books?author=frank%20herbert'
curl localhost:8000/books/1
curl -X PUT localhost:8000/books/1 -H 'Content-Type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1966}'
curl -X DELETE localhost:8000/books/1      # 204
curl localhost:8000/health                  # {"status": "ok", "database": "ok"}
```

## Project layout

```
app.py                 # validation, SQLite repository, HTTP handler, CLI entry point
test_app.py            # unit + integration tests (pytest)
requirements-dev.txt   # test dependencies
```
