# Book Collection API

A small REST API for managing a book collection. Built with Python's standard
library (`http.server` and `sqlite3`), so the service has **no runtime
dependencies**. Tests use `pytest`.

## Requirements

- Python 3.9+
- pytest (only for running the tests)

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -e ".[test]"
```

## Run

```bash
python -m bookapi                          # http://127.0.0.1:8000, data in books.db
python -m bookapi --port 9000 --db my.db   # custom port / database file
```

Data is stored in SQLite and survives restarts.

## Test

```bash
pytest
```

The suite contains unit tests for validation and storage, plus integration
tests that start the real HTTP server on an ephemeral port.

## API

All request and response bodies are JSON.

| Method | Path          | Description                                  | Success |
|--------|---------------|----------------------------------------------|---------|
| POST   | `/books`      | Create a book                                | 201 + `Location` header |
| GET    | `/books`      | List books; optional `?author=` filter       | 200     |
| GET    | `/books/{id}` | Get one book                                 | 200     |
| PUT    | `/books/{id}` | Replace a book's fields                      | 200     |
| DELETE | `/books/{id}` | Delete a book                                | 204     |
| GET    | `/health`     | Health check (verifies the database responds) | 200     |

### Book fields

| Field    | Type    | Required | Notes                                   |
|----------|---------|----------|-----------------------------------------|
| `id`     | integer | —        | Assigned by the server                  |
| `title`  | string  | yes      | Non-blank                               |
| `author` | string  | yes      | Non-blank                               |
| `year`   | integer | no       | Between 1 and next calendar year        |
| `isbn`   | string  | no       | Stored as given (not checked for format) |

Strings are trimmed of surrounding whitespace. `PUT` is a full replacement:
any optional field omitted from the body is cleared to `null`.

`?author=` matches the author exactly, ignoring case (`?author=frank%20herbert`
matches `Frank Herbert`).

### Errors

Errors return `{"error": "<message>"}`. Validation failures add a `details`
object mapping each invalid field to a message:

```json
{"error": "validation failed", "details": {"title": "is required"}}
```

| Status | When                                              |
|--------|---------------------------------------------------|
| 400    | Invalid JSON, non-object body, or validation error |
| 404    | Unknown route, non-numeric id, or book not found   |
| 405    | Method not supported on that route (includes `Allow` header) |
| 413    | Request body larger than 1 MB                      |
| 503    | `/health` when the database is unavailable         |

## Examples

```bash
curl -i -X POST localhost:8000/books \
  -H 'Content-Type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593"}'

curl localhost:8000/books?author=Frank%20Herbert
curl -X PUT localhost:8000/books/1 -H 'Content-Type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965}'
curl -i -X DELETE localhost:8000/books/1
curl localhost:8000/health
```

## Project layout

```
bookapi/
  __main__.py   CLI entry point (python -m bookapi)
  server.py     HTTP routing, status codes, JSON encoding
  storage.py    SQLite persistence (BookStore)
  validation.py Payload validation
tests/
  test_api.py        HTTP integration tests
  test_storage.py    storage unit tests
  test_validation.py validation unit tests
```
