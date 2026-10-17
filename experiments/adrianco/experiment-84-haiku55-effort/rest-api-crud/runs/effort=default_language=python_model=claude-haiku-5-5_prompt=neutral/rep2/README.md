# Books API

A REST API for managing a book collection. Written in Python using only the
standard library (`http.server` for HTTP, `sqlite3` for storage), so there
are no runtime dependencies. `pytest` is needed only to run the tests.

## Setup

Requires Python 3.8 or newer. Developed and tested on 3.13.

```bash
python3 -m venv venv
source venv/bin/activate
pip install pytest        # only needed to run the tests
```

## Run

```bash
python -m books_api                       # http://127.0.0.1:8000, database ./books.db
python -m books_api --port 9000
python -m books_api --db /path/to/my.db
```

Options:

| Flag     | Default                                 |
|----------|-----------------------------------------|
| `--host` | `127.0.0.1`                             |
| `--port` | `8000`                                  |
| `--db`   | `$BOOKS_DB_PATH` or `books.db`          |

## Test

```bash
python -m pytest
```

## Data model

| Field    | Type    | Rules                                                                 |
|----------|---------|-----------------------------------------------------------------------|
| `id`     | integer | Assigned by the server. Read-only.                                    |
| `title`  | string  | Required. Trimmed, non-blank, at most 500 characters.                 |
| `author` | string  | Required. Trimmed, non-blank, at most 300 characters.                 |
| `year`   | integer | Optional. Between 1 and next calendar year. Null if omitted.          |
| `isbn`   | string  | Optional. ISBN-10 or ISBN-13, hyphens and spaces allowed, checksum verified. Stored without separators, upper-case. Must be unique. Null if omitted or blank. |

## Endpoints

| Method   | Path          | Success                | Description                                    |
|----------|---------------|------------------------|------------------------------------------------|
| `POST`   | `/books`      | `201` + `Location`     | Create a book.                                 |
| `GET`    | `/books`      | `200`                  | List all books. Supports `?author=` filter.    |
| `GET`    | `/books/{id}` | `200`                  | Get one book.                                  |
| `PUT`    | `/books/{id}` | `200`                  | Replace a book. Same rules as create.          |
| `DELETE` | `/books/{id}` | `204` (no body)        | Delete a book.                                 |
| `GET`    | `/health`     | `200` / `503`          | Health check. `503` if the database is unreachable. |

`PUT` replaces the whole record. Omitting `year` or `isbn` clears them.

The `?author=` filter is an exact match that ignores case:
`/books?author=frank%20herbert` matches "Frank Herbert".

## Examples

```bash
# Create
curl -i -X POST http://127.0.0.1:8000/books \
  -H 'Content-Type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0-306-40615-7"}'

# List, filtered by author
curl 'http://127.0.0.1:8000/books?author=Frank%20Herbert'

# Get, update, delete
curl http://127.0.0.1:8000/books/1
curl -X PUT http://127.0.0.1:8000/books/1 -H 'Content-Type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965}'
curl -X DELETE http://127.0.0.1:8000/books/1

# Health
curl http://127.0.0.1:8000/health
```

## Errors

Errors are JSON of the form `{"error": "..."}`.

| Status | When                                                                  |
|--------|-----------------------------------------------------------------------|
| `400`  | Invalid JSON, non-object body, or validation failure. Validation failures also include `details`, a map of field to message. |
| `404`  | Unknown route, unknown or non-numeric book id.                        |
| `405`  | Known route, unsupported method. The `Allow` header lists valid methods. |
| `409`  | ISBN already used by another book.                                    |
| `413`  | Request body larger than 1 MiB.                                       |
| `500`  | Unexpected server error (logged).                                     |

Validation error example:

```json
{"error": "validation failed", "details": {"title": "is required", "author": "is required"}}
```

## Layout

```
books_api/
  __main__.py    command-line entry point
  server.py      HTTP routing, JSON responses, error handling
  database.py    SQLite storage (BookRepository)
  validation.py  input validation and ISBN checks
tests/
  conftest.py        runs a real server on a free port for each test
  test_api.py        HTTP-level tests of every endpoint and error case
  test_repository.py storage-layer tests
  test_validation.py validation rule tests
```
