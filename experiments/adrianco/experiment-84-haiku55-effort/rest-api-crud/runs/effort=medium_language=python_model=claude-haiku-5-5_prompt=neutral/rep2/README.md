# Books API

A REST API for managing a book collection. It is built on the Python standard
library (`wsgiref` for HTTP, `sqlite3` for storage), so the only dependency is
pytest for running the tests.

## Setup

Requires Python 3.10 or newer.

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt
```

## Run

```bash
python -m books
```

The server listens on `http://127.0.0.1:8000` by default. Configure it with
environment variables:

| Variable        | Default         | Purpose                         |
|-----------------|-----------------|---------------------------------|
| `HOST`          | `127.0.0.1`     | Address to bind to              |
| `PORT`          | `8000`          | Port to listen on               |
| `BOOKS_DB_PATH` | `books.db`      | SQLite database file (created on first run) |

Example:

```bash
PORT=8080 BOOKS_DB_PATH=/tmp/books.db python -m books
```

## Test

```bash
pytest
```

The suite has unit tests for validation (`tests/test_validation.py`) and
API tests (`tests/test_api.py`). The API tests drive the WSGI app directly, and
one test starts a real HTTP server for a full round trip.

## API

All requests and responses use JSON.

### Book fields

| Field    | Type    | Required | Notes                                              |
|----------|---------|----------|----------------------------------------------------|
| `id`     | integer | —        | Assigned by the server                             |
| `title`  | string  | yes      | Non-empty, up to 255 characters                    |
| `author` | string  | yes      | Non-empty, up to 255 characters                    |
| `year`   | integer | no       | Between 1 and next year. `null` or omitted if unknown |
| `isbn`   | string  | no       | Valid ISBN-10 or ISBN-13 (checksum is verified). Hyphens and spaces are allowed and stripped. Must be unique across books |

### Endpoints

| Method   | Path          | Success | Description                              |
|----------|---------------|---------|------------------------------------------|
| `POST`   | `/books`      | `201`   | Create a book. Response includes `Location`. |
| `GET`    | `/books`      | `200`   | List books in id order. Filter with `?author=` (case-insensitive exact match). |
| `GET`    | `/books/{id}` | `200`   | Get one book.                            |
| `PUT`    | `/books/{id}` | `200`   | Replace a book. The body is a full book, so `title` and `author` are required. Omitted `year` or `isbn` are cleared. |
| `DELETE` | `/books/{id}` | `204`   | Delete a book. No response body.         |
| `GET`    | `/health`     | `200`   | `{"status": "ok"}`. Returns `503` if the database is unreachable. |

### Errors

Error responses have the form `{"error": "<message>"}`. Validation failures
add a `details` object that maps each invalid field to a message.

| Status | When                                                     |
|--------|----------------------------------------------------------|
| `400`  | Invalid JSON, a body that is not an object, or validation failure |
| `404`  | Unknown book id or unknown path                          |
| `405`  | Wrong method for the path; the `Allow` header lists valid methods |
| `409`  | ISBN already used by another book                        |
| `413`  | Request body over 64 KB                                  |
| `500`  | Unexpected server error (logged, details not returned)   |

### Examples

```bash
# Create
curl -i -X POST http://127.0.0.1:8000/books \
  -H 'Content-Type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965, "isbn": "978-0-306-40615-7"}'

# List, filtered by author
curl 'http://127.0.0.1:8000/books?author=Frank%20Herbert'

# Update
curl -X PUT http://127.0.0.1:8000/books/1 \
  -H 'Content-Type: application/json' \
  -d '{"title": "Dune", "author": "Frank Herbert", "year": 1965}'

# Delete
curl -X DELETE http://127.0.0.1:8000/books/1

# Health
curl http://127.0.0.1:8000/health
```

## Project layout

```
books/
  __main__.py    # python -m books
  app.py         # WSGI app, routing, HTTP server setup
  db.py          # SQLite storage (BookStore)
  validation.py  # Input validation and ISBN checks
tests/
  conftest.py       # Fixtures and a WSGI test client
  test_api.py       # Endpoint tests, plus a live-server round trip
  test_validation.py
```
