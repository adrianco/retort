# Books API

A small REST API for managing a book collection, written in Python using only
the standard library (`http.server` + `sqlite3`). There are no runtime
dependencies; `pytest` is needed only to run the tests.

## Requirements

- Python 3.10+ (developed and tested on 3.14)

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt   # only needed for running tests
```

## Run

```bash
python -m books_api                    # http://127.0.0.1:8000, data in ./books.db
python -m books_api --host 0.0.0.0 --port 9000 --db /path/to/books.db
```

The same options can be set with the `BOOKS_HOST`, `BOOKS_PORT` and `BOOKS_DB`
environment variables. The SQLite database and schema are created on first run.

## Test

```bash
python -m pytest
```

The tests cover validation rules, the SQLite store, and every endpoint
end-to-end against a real server started on a random port with a temporary
database.

## API

All responses are JSON (`Content-Type: application/json`), apart from the
empty `204` response to a delete.

| Method | Path          | Success | Description |
|--------|---------------|---------|-------------|
| GET    | `/health`     | 200     | Service and database health |
| POST   | `/books`      | 201     | Create a book; returns it with a `Location` header |
| GET    | `/books`      | 200     | List all books; `?author=` filters by author |
| GET    | `/books/{id}` | 200     | Get one book |
| PUT    | `/books/{id}` | 200     | Replace a book's fields |
| DELETE | `/books/{id}` | 204     | Delete a book |

### Book fields

| Field    | Type    | Rules |
|----------|---------|-------|
| `title`  | string  | **Required**, non-blank, at most 500 characters (whitespace trimmed) |
| `author` | string  | **Required**, non-blank, at most 500 characters (whitespace trimmed) |
| `year`   | integer | Optional; between -5000 and next year |
| `isbn`   | string  | Optional; ISBN-10 or ISBN-13. Hyphens and spaces are stripped. Must be unique. |

`id` is assigned by the server. Unknown fields are rejected.

### Behaviour notes

- **PUT is a full replacement.** `title` and `author` must always be sent;
  omitted optional fields (`year`, `isbn`) are cleared. If the body contains
  an `id`, it must match the URL.
- **`?author=` filter** is an exact match that ignores case and surrounding
  whitespace, e.g. `?author=jane%20austen` matches `Jane Austen`.
- Books are listed in creation (id) order.

### Errors

Errors are returned as `{"error": "<message>"}`, with a `details` object
mapping field names to messages for validation failures.

| Status | When |
|--------|------|
| 400 | Missing, malformed or invalid JSON body; validation failure |
| 404 | Unknown book id or route |
| 405 | Method not supported on the route (an `Allow` header is included) |
| 409 | ISBN already belongs to another book |
| 413 | Request body larger than 64 KiB |
| 500 | Unexpected server error |

### Example

```bash
curl -X POST localhost:8000/books \
  -H 'Content-Type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0441013593"}'
# 201 {"id": 1, "title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "9780441013593"}

curl -X POST localhost:8000/books -H 'Content-Type: application/json' -d '{"year": 1965}'
# 400 {"error": "Validation failed", "details": {"title": "Title is required", "author": "Author is required"}}

curl 'localhost:8000/books?author=frank%20herbert'
curl localhost:8000/books/1
curl -X PUT localhost:8000/books/1 -H 'Content-Type: application/json' \
  -d '{"title": "Dune Messiah", "author": "Frank Herbert", "year": 1969}'
curl -X DELETE localhost:8000/books/1      # 204
```

## Project layout

```
books_api/
  __main__.py     command-line entry point
  server.py       HTTP routing, JSON responses and status codes
  store.py        SQLite persistence
  validation.py   request payload validation
tests/            pytest suite (validation, store, API end-to-end)
```
